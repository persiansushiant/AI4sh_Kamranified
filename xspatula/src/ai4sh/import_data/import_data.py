'''
Created on 28 Jan 2026

@author: thomas gumbricht
'''

# Standard library imports
import os
import json

from copy import deepcopy

# Application package imports
from src.lib.pilot import Full_path_locate
from src.utils.json_read_write import Dump_json
from src.utils.csv_read_write import Read_csv, Read_excel
from src.postgres import Get_schema_table
from src.postgres.pg_ai4sh import PG_manage_AI4SH

from app.services.workspace_context import services


def _format_trace_message(message, details):
    """Preserve legacy details inside the current trace message."""
    return (
        f"{message} | "
        f"{json.dumps(details, ensure_ascii=False, default=str)}"
    )


# Column names whose values must never be forced to lowercase during import.
# Add entries here to extend the exclusion list.
NO_LOWER_COLS = frozenset({
    'display_name',
    'abstract',
    'title',
    'label',
})

# Define classification levels for substances.
CLASSIFICATION_TABLE_D = {
    'manage_order': [
        'manage_family',
        'manage_genus',
        'manage_species',
    ],
    'manage_family': [
        'manage_genus',
        'manage_species',
    ],
    'manage_genus': [
        'manage_species',
    ],
}

CLASSIFICATION_CHILDREN_D = {
    'manage_family': {
        'table': 'family',
        'parent_id_name': 'order_id__order_name',
    },
    'manage_genus': {
        'table': 'genus',
        'parent_id_name': 'family_id__family_name',
    },
    'manage_species': {
        'table': 'species',
        'parent_id_name': 'genus_id__genus_name',
    },
}

SPECIAL_SEARCH_TABLES_D = {
    'observation.campaign': '_Retrieve_dataset_alias',
    'observation.observation': (
        '_Retrieve_sample_id_from_observation_log'
    ),
    'observation.observation_measurement': (
        '_Retrieve_quantity_indicator_id_from_provision'
    ),
}


class Process_import_JSON(Get_schema_table):
    '''Class for managing processes.'''

    def __init__(self, process_S, pg_session_C):
        self.verbose = process_S.process.verbose
        self.process_S = process_S
        self.pg_session_C = pg_session_C

        self.verbose = process_S.process.verbose
        self.process_S = process_S

        self.pg_ai4sh_C = PG_manage_AI4SH(pg_session_C)

    def _Lower_text_values(self, queryD, schema, table):
        """
        Lowercase text-column values while preserving NO_LOWER_COLS.
        """
        text_cols = self.pg_session_C._Get_text_columns(
            schema,
            table,
        )

        return {
            k: (
                v.lower()
                if (
                    isinstance(v, str)
                    and k.lower() in text_cols
                    and k.lower() not in NO_LOWER_COLS
                )
                else v
            )
            for k, v in queryD.items()
        }

    def _Sub_process(self, json_file_key):
        # Direct to the appropriate subprocess.
        if self.process_S.process.process.startswith('translate'):
            return self._Translate_tabular_data(json_file_key)

        elif self.process_S.process.process.startswith('manage'):
            services().log(
                section="sql",
                status="info",
                message=_format_trace_message(
                    "Dispatching manage process to PostgreSQL importer",
                    {
                        "process": self.process_S.process.process,
                        "has_database_session": bool(self.pg_session_C),
                        "overwrite": self.process_S.process.overwrite,
                        "delete": self.process_S.process.delete,
                    },
                ),
            )

            if not self.pg_session_C:
                services().log(
                    section="sql",
                    status="error",
                    message=_format_trace_message(
                        "Manage process has no PostgreSQL connection",
                        {
                            "process": self.process_S.process.process,
                        },
                    ),
                )

                print(
                    '❌ ERROR - Adding data to Postgres requires a '
                    'database connection. Please define a Postgres '
                    'database in scheme file.'
                )

                return None

            return self._Add_JSON_data()

        else:
            error_msg = (
                '\n❌ ERROR process %s \n'
                '     not available in Process_translate'
                % self.process_S.process.process
            )

            if self.pg_session_C:
                self.pg_session_C.log(error_msg)

            return None

    def _Dump_translation(self):
        '''Dump the structured data to JSON.'''
        if not self.process_D:
            print('    ❌ ERROR - No data to dump')
            return None

        Dump_json(self.dst_FPN, self.process_D)

        if self.verbose > 0:
            print('    ✅ Created JSON: %s' % self.dst_FPN)

    def _Set_dst_FPN(self, json_file_key):
        dst_FN = (
            '%s.json'
            % self.process_S.process.parameters.process
        )

        self.dst_FPN = os.path.join(self.dst_FP, dst_FN)

        if (
            os.path.exists(self.dst_FPN)
            and not self.process_S.process.overwrite
        ):
            if self.verbose > 1:
                print(
                    '    🟡 JSON destination file already exists. '
                    'Use overwrite option to replace.'
                )
                print(
                    '    🟡 Existing JSON file: %s'
                    % self.dst_FPN
                )

            return None

        elif (
            os.path.exists(self.dst_FPN)
            and self.process_S.process.delete
        ):
            os.remove(self.dst_FPN)

            if self.verbose > 1:
                print(
                    '    ✅ Existing JSON file deleted: %s'
                    % self.dst_FPN
                )

            return None

        elif (
            os.path.exists(self.dst_FPN)
            and self.process_S.process.overwrite
        ):
            os.remove(self.dst_FPN)

        return True

    def _Extract_tabular_data(self, column_L, data_L_L):
        '''Extract records from the tabular data file.'''
        self.record_D = {}

        for row, data_L in enumerate(data_L_L):
            self.record_D[row] = dict(zip(column_L, data_L))

            keys_to_remove = []

            for key in self.record_D[row]:
                if (
                    self.record_D[row][key] == 'null'
                    or self.record_D[row][key] == ''
                ):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                self.record_D[row].pop(key)

        return True

    def _Structure_data(self):
        """
        Structure extracted records into executable JSON processes.

        String values are normalized except for NO_LOWER_COLS.
        Classification processes also generate their lower levels.
        """
        main_process_D = {
            "root_process_id": "import_tabular_data",
            "process": self.process_S.process.parameters.process,
            "delete": False,
            "overwrite": False,
            "parameters": {},
        }

        self.process_D = {"process": []}

        for rec in self.record_D:
            process_D = deepcopy(main_process_D)

            # Preserve presentation text while normalizing other strings.
            process_D['parameters'] = {
                k: (
                    v.lower()
                    if (
                        isinstance(v, str)
                        and k.lower() not in NO_LOWER_COLS
                    )
                    else v
                )
                for k, v in self.record_D[rec].items()
            }

            self.process_D['process'].append(process_D)

        # Add the generic term to lower classification levels.
        if (
            self.process_S.process.parameters.process
            in CLASSIFICATION_TABLE_D
        ):
            for rec in self.record_D:
                for lower_level in CLASSIFICATION_TABLE_D[
                    self.process_S.process.parameters.process
                ]:
                    name = self.record_D[rec]['name']

                    parent_column_id_name = (
                        CLASSIFICATION_CHILDREN_D[lower_level][
                            'parent_id_name'
                        ]
                    )

                    alias = (
                        self.record_D[rec]['alias']
                        if 'alias' in self.record_D[rec]
                        else None
                    )

                    display_name = (
                        self.record_D[rec]['display_name']
                        if 'display_name' in self.record_D[rec]
                        else None
                    )

                    abstract = (
                        self.record_D[rec]['abstract']
                        if 'abstract' in self.record_D[rec]
                        else None
                    )

                    process = lower_level

                    process_D = deepcopy(main_process_D)
                    process_D['process'] = process

                    process_D['parameters'] = {
                        'name': name,
                        parent_column_id_name: name,
                        'alias': alias,
                        'display_name': display_name,
                        'abstract': abstract,
                    }

                    self.process_D['process'].append(process_D)

    def _Translate_tabular_data(self, json_file_key):
        """Translate an Excel or CSV source into a JSON process file."""
        source_parameter = (
            self.process_S.process.parameters.tabular_data_path
        )

        target_process = self.process_S.process.parameters.process

        destination_parameter = (
            self.process_S.process.parameters.dst_path
        )

        services().log(
            section="excel",
            status="info",
            message=_format_trace_message(
                "Resolving tabular source file",
                {
                    "source_path": source_parameter,
                    "target_process": target_process,
                    "command_file": json_file_key,
                },
            ),
        )

        tabular_data_path = Full_path_locate(
            os.path.split(json_file_key)[0],
            source_parameter,
        )

        if not tabular_data_path:
            services().log(
                section="excel",
                status="error",
                message=_format_trace_message(
                    "Tabular source file could not be resolved",
                    {
                        "source_path": source_parameter,
                        "command_file": json_file_key,
                    },
                ),
            )
            return None

        services().log(
            section="excel",
            status="success",
            message=_format_trace_message(
                "Tabular source file resolved",
                {
                    "source_file": tabular_data_path,
                    "file_exists": os.path.exists(tabular_data_path),
                    "file_type": os.path.splitext(
                        tabular_data_path
                    )[1].lower().lstrip("."),
                },
            ),
        )

        self.dst_FP = Full_path_locate(
            os.path.split(json_file_key)[0],
            destination_parameter,
            True,
        )

        services().log(
            section="excel",
            status="info",
            message=_format_trace_message(
                "Preparing generated process destination",
                {
                    "destination_path": self.dst_FP,
                    "target_process": target_process,
                },
            ),
        )

        if not self._Set_dst_FPN(json_file_key):
            services().log(
                section="excel",
                status="error",
                message=_format_trace_message(
                    "Generated process destination is not writable",
                    {
                        "destination_path": self.dst_FP,
                        "output_file": getattr(self, "dst_FPN", None),
                        "overwrite": self.process_S.process.overwrite,
                        "delete": self.process_S.process.delete,
                    },
                ),
            )
            return None

        source_extension = os.path.splitext(
            tabular_data_path
        )[1].lower()

        if source_extension == ".csv":
            services().log(
                section="excel",
                status="info",
                message=_format_trace_message(
                    "Reading CSV source through tabular importer",
                    {
                        "source_file": tabular_data_path,
                        "target_process": target_process,
                    },
                ),
            )

            result = Read_csv(tabular_data_path)

        elif source_extension == ".xlsx":
            result = Read_excel(tabular_data_path)

        else:
            services().log(
                section="excel",
                status="error",
                message=_format_trace_message(
                    "Tabular source file type is not supported",
                    {
                        "source_file": tabular_data_path,
                        "file_type": source_extension,
                        "supported_types": [".csv", ".xlsx"],
                    },
                ),
            )
            return None

        if not result:
            services().log(
                section="excel",
                status="error",
                message=_format_trace_message(
                    "Tabular source returned no readable data",
                    {
                        "source_file": tabular_data_path,
                        "target_process": target_process,
                    },
                ),
            )
            return None

        column_L, data_L_L = result

        services().log(
            section="excel",
            status="success",
            message=_format_trace_message(
                "Tabular data received by translation process",
                {
                    "source_file": tabular_data_path,
                    "rows": len(data_L_L),
                    "columns": len(column_L),
                    "column_names": column_L,
                    "target_process": target_process,
                },
            ),
        )

        services().log(
            section="excel",
            status="info",
            message=_format_trace_message(
                "Extracting tabular rows",
                {
                    "source_rows": len(data_L_L),
                    "target_process": target_process,
                },
            ),
        )

        if not self._Extract_tabular_data(column_L, data_L_L):
            services().log(
                section="excel",
                status="error",
                message=_format_trace_message(
                    "Tabular rows could not be extracted",
                    {
                        "source_file": tabular_data_path,
                        "source_rows": len(data_L_L),
                    },
                ),
            )
            return None

        services().log(
            section="excel",
            status="success",
            message=_format_trace_message(
                "Tabular rows extracted",
                {
                    "source_rows": len(data_L_L),
                    "extracted_records": len(self.record_D),
                },
            ),
        )

        services().log(
            section="excel",
            status="info",
            message=_format_trace_message(
                "Structuring generated process commands",
                {
                    "target_process": target_process,
                    "extracted_records": len(self.record_D),
                },
            ),
        )

        self._Structure_data()

        generated_commands = len(
            self.process_D.get("process", [])
        )

        services().log(
            section="excel",
            status="success",
            message=_format_trace_message(
                "Process commands generated from tabular data",
                {
                    "target_process": target_process,
                    "source_rows": len(data_L_L),
                    "generated_commands": generated_commands,
                },
            ),
        )

        services().log(
            section="excel",
            status="info",
            message=_format_trace_message(
                "Writing generated process JSON",
                {
                    "output_file": self.dst_FPN,
                    "generated_commands": generated_commands,
                },
            ),
        )

        self._Dump_translation()

        output_exists = os.path.exists(self.dst_FPN)

        services().log(
            section="excel",
            status="success" if output_exists else "error",
            message=_format_trace_message(
                (
                    "Generated process JSON written successfully"
                    if output_exists
                    else "Generated process JSON was not created"
                ),
                {
                    "output_file": self.dst_FPN,
                    "file_exists": output_exists,
                    "file_size_bytes": (
                        os.path.getsize(self.dst_FPN)
                        if output_exists
                        else 0
                    ),
                    "generated_commands": generated_commands,
                },
            ),
        )

        if not output_exists:
            return None

        return self.dst_FPN

    def _Insert(self, query_D, schema_S, table_S, model_name_S):
        """Insert one record into PostgreSQL and trace the result."""
        normalized_query_D = self._Lower_text_values(
            query_D,
            schema_S,
            table_S,
        )

        services().log(
            section="sql",
            status="info",
            message=_format_trace_message(
                "Attempting PostgreSQL insert",
                {
                    "process": self.process_S.process.process,
                    "schema": schema_S,
                    "table": table_S,
                    "record": model_name_S,
                    "parameter_names": list(normalized_query_D.keys()),
                    "parameter_count": len(normalized_query_D),
                },
            ),
        )

        try:
            success = self.pg_session_C._Check_insert_single_record(
                normalized_query_D,
                schema_S,
                table_S,
            )

        except Exception as error:
            services().log(
                section="sql",
                status="error",
                message=_format_trace_message(
                    "PostgreSQL insert raised an exception",
                    {
                        "process": self.process_S.process.process,
                        "schema": schema_S,
                        "table": table_S,
                        "record": model_name_S,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    },
                ),
            )
            raise

        if not success:
            services().log(
                section="sql",
                status="error",
                message=_format_trace_message(
                    "PostgreSQL insert was rejected",
                    {
                        "process": self.process_S.process.process,
                        "schema": schema_S,
                        "table": table_S,
                        "record": model_name_S,
                    },
                ),
            )

            print(
                '   ❌ ERROR - could not insert record <%s> '
                'in table %s.%s'
                % (model_name_S, schema_S, table_S)
            )

            return success

        services().log(
            section="sql",
            status="success",
            message=_format_trace_message(
                "PostgreSQL record inserted",
                {
                    "process": self.process_S.process.process,
                    "schema": schema_S,
                    "table": table_S,
                    "record": model_name_S,
                },
            ),
        )

        return success

    def _Measurement_record(self, main_query_D):
        """
        Retrieve observation and indicator IDs for a measurement.

        Resolve the indicator against the selected observation log.
        """
        measurement_indicators_L = (
            self.pg_session_C
            ._Retrieve_observation_log_indicators_from_log_name(
                main_query_D[
                    'observation_log_id__observation_log_name'
                ]
            )
        )

        if not measurement_indicators_L:
            print(
                '.  ❌ ERROR: could not retrieve indicators '
                'for observation_log %s'
                % main_query_D[
                    'observation_log_id__observation_log_name'
                ]
            )
            return None

        indicator_D = dict(measurement_indicators_L)

        if main_query_D['indicator_id__indicator_name'] not in indicator_D:
            print(
                '.  ❌ ERROR: indicator %s not found '
                'for observation log %s'
                % (
                    main_query_D['indicator_id__indicator_name'],
                    main_query_D[
                        'observation_log_id__observation_log_name'
                    ],
                )
            )
            print(
                '.     Available indicators for this observation '
                'log are: %s'
                % list(indicator_D.keys())
            )
            return None

        if not main_query_D['indicator_id__indicator_name'] in indicator_D:
            print(
                '.  ❌ ERROR: indicator %s not found '
                'for observation log %s'
                % (
                    main_query_D['indicator_id__indicator_name'],
                    main_query_D[
                        'observation_log_id__observation_log_name'
                    ],
                )
            )
            print(
                '.     Available indicators for this observation '
                'log are: %s'
                % list(indicator_D.keys())
            )
            return None

        indicator_id = indicator_D[
            main_query_D['indicator_id__indicator_name']
        ]

        observation_id = (
            self.pg_session_C
            ._Retrieve_observation_id_from_observation(main_query_D)
        )

        if not observation_id:
            print(
                '.  ❌ ERROR: could not retrieve observation '
                'id for measurement record'
            )
            return None

        update_main_query_D = {
            'observation_id': observation_id,
            'indicator_id': indicator_id,
            'value': main_query_D['value'],
            'standard_deviation': main_query_D['standard_deviation'],
            'n_repeat': main_query_D['n_repeat'],
        }

        if update_main_query_D['standard_deviation'] == -999.999:
            update_main_query_D.pop('standard_deviation')

        return update_main_query_D

    def _Add_JSON_data(self):
        services().log(
            section="sql",
            status="info",
            message=_format_trace_message(
                "Starting JSON-to-PostgreSQL import",
                {
                    "process": self.process_S.process.process,
                    "overwrite": self.process_S.process.overwrite,
                    "delete": self.process_S.process.delete,
                },
            ),
        )

        if self.verbose > 1:
            print('Adding JSON data to Postgres')

        schema_table_query_D = self._Get_process_schema_table()

        services().log(
            section="sql",
            status="success" if schema_table_query_D else "error",
            message=_format_trace_message(
                (
                    "Process parameters mapped to schema tables"
                    if schema_table_query_D
                    else (
                        "Process parameters could not be mapped "
                        "to schema tables"
                    )
                ),
                {
                    "process": self.process_S.process.process,
                    "schema_table_count": (
                        len(schema_table_query_D)
                        if schema_table_query_D
                        else 0
                    ),
                    "schema_tables": (
                        list(schema_table_query_D.keys())
                        if schema_table_query_D
                        else []
                    ),
                },
            ),
        )

        if not schema_table_query_D:
            return None

        if self.verbose > 1:
            print('Schema table query dictionary retrieved')

        query_D = {
            'process': self.process_S.process.process,
        }

        records = self.pg_session_C._Multi_search(
            query_D,
            ['parameter', 'in_schema', 'in_table', 'write'],
            'process',
            'process_parameter_schema_table',
        )

        services().log(
            section="sql",
            status="success" if records else "error",
            message=_format_trace_message(
                (
                    "Database mapping records retrieved"
                    if records
                    else "No database mapping records found for process"
                ),
                {
                    "process": self.process_S.process.process,
                    "mapping_record_count": (
                        len(records) if records else 0
                    ),
                },
            ),
        )

        if not records:
            return None

        dst_schema = records[0][1]

        dst_tables = set([item[2] for item in records])

        # Preserve the existing destination-table ordering.
        dst_tables = list(dst_tables)
        dst_tables.sort(key=len)

        dst_main_table = dst_tables[0]

        main_table_key = '%s.%s' % (
            dst_schema,
            dst_main_table,
        )

        services().log(
            section="sql",
            status="info",
            message=_format_trace_message(
                "Resolved PostgreSQL import destination",
                {
                    "process": self.process_S.process.process,
                    "destination_schema": dst_schema,
                    "destination_tables": dst_tables,
                    "main_table": dst_main_table,
                    "main_table_key": main_table_key,
                },
            ),
        )

        if main_table_key not in schema_table_query_D:
            services().log(
                section="sql",
                status="error",
                message=_format_trace_message(
                    "Main destination table is missing "
                    "from mapped process data",
                    {
                        "process": self.process_S.process.process,
                        "main_table_key": main_table_key,
                        "available_schema_tables": list(
                            schema_table_query_D.keys()
                        ),
                    },
                ),
            )
            return None

        # Separate the main table payload from related tables.
        main_query_D = schema_table_query_D.pop(main_table_key)

        services().log(
            section="sql",
            status="success",
            message=_format_trace_message(
                "Main table payload prepared",
                {
                    "process": self.process_S.process.process,
                    "main_table_key": main_table_key,
                    "parameter_names": list(main_query_D.keys()),
                    "specific_table_count": len(schema_table_query_D),
                },
            ),
        )

        if self.verbose > 1:
            print(
                '      Managing main schema.table: %s.%s'
                % (dst_schema, dst_main_table)
            )

        if main_table_key in SPECIAL_SEARCH_TABLES_D:
            retrieve_function = getattr(
                self.pg_ai4sh_C,
                SPECIAL_SEARCH_TABLES_D[main_table_key],
            )

            record = retrieve_function(
                main_query_D,
                self.pg_session_C,
            )

            if not record:
                print(
                    '.  ❌ ERROR: could not retrieve record '
                    'for %s.%s'
                    % (dst_schema, dst_main_table)
                )
                return None

            # Replace the lookup field with its resolved ID field.
            main_query_D.pop(record[0])
            main_query_D[record[1]] = record[2]

        elif main_table_key == 'observation.measurement':
            main_query_D = self._Measurement_record(main_query_D)

            if not main_query_D:
                return None

        # Remove fields marked as non-writable in the process mapping.
        for rec in records:
            if not rec[3] and rec[0] in main_query_D:
                main_query_D.pop(rec[0])

            if not rec[3] and rec[0] in schema_table_query_D:
                schema_table_query_D.pop(rec[0])

        table_keys = self.pg_session_C._Get_table_keys(
            dst_schema,
            dst_main_table,
        )

        if not 'name' in main_query_D:
            column_report_name = ",".join(
                [item[0] for item in table_keys]
            )
        else:
            column_report_name = main_query_D['name']

        services().log(
            section="sql",
            status="info",
            message=_format_trace_message(
                "Checking whether main record already exists",
                {
                    "process": self.process_S.process.process,
                    "schema": dst_schema,
                    "table": dst_main_table,
                    "record": column_report_name,
                },
            ),
        )

        record_id = self.pg_session_C._Single_search_tab_keys(
            self._Lower_text_values(
                main_query_D,
                dst_schema,
                dst_main_table,
            ),
            ['id'],
            dst_schema,
            dst_main_table,
        )

        services().log(
            section="sql",
            status=(
                "error"
                if record_id == 'fk_error'
                else "success"
            ),
            message=_format_trace_message(
                (
                    "Foreign-key resolution failed while checking record"
                    if record_id == 'fk_error'
                    else (
                        "Existing PostgreSQL record found"
                        if record_id
                        else "No existing PostgreSQL record found"
                    )
                ),
                {
                    "process": self.process_S.process.process,
                    "schema": dst_schema,
                    "table": dst_main_table,
                    "record": column_report_name,
                    "record_exists": (
                        bool(record_id)
                        and record_id != 'fk_error'
                    ),
                    "record_id": (
                        record_id[0]
                        if record_id and record_id != 'fk_error'
                        else None
                    ),
                },
            ),
        )

        if record_id == 'fk_error':
            print(
                '.  ❌ ERROR: could not retrieve foreign key '
                'for %s.%s'
                % (dst_schema, dst_main_table)
            )
            return None

        elif record_id and self.process_S.process.delete:
            self._Delete(
                'id = %s' % record_id[0],
                dst_schema,
                dst_main_table,
                column_report_name,
            )

            # Preserve the existing deletion logic.
            where_statement = where_statement.replace(
                'id',
                'model_id',
            )

            for schema_table in schema_table_query_D:
                schema, table = schema_table.split('.')

                self._Delete(
                    where_statement,
                    schema,
                    table,
                    column_report_name,
                )

                print(
                    '.   ✅ Record %s deleted from %s.%s'
                    % (column_report_name, schema, table)
                )

            return None

        elif not record_id and self.process_S.process.delete:
            if self.verbose > 1:
                print(
                    '.   ✅ Nothing to delete, record %s not found'
                    % column_report_name
                )

            return None

        elif record_id and self.process_S.process.overwrite:
            success = self._Update(
                main_query_D,
                'hardware',
                'model',
                column_report_name,
            )

            if success and self.verbose > 1:
                print(
                    '.   ✅ Nothing to delete, record %s not found'
                    % column_report_name
                )

            return None

        elif record_id:
            services().log(
                section="sql",
                status="success",
                message=_format_trace_message(
                    "Existing PostgreSQL record skipped",
                    {
                        "process": self.process_S.process.process,
                        "schema": dst_schema,
                        "table": dst_main_table,
                        "record": column_report_name,
                        "record_id": record_id[0],
                        "reason": "overwrite is disabled",
                    },
                ),
            )

            if self.verbose > 1:
                print(
                    '.   ✅ Record %s already registered, '
                    'use overwrite to update'
                    % column_report_name
                )

        elif not record_id:
            success = self._Insert(
                main_query_D,
                dst_schema,
                dst_main_table,
                column_report_name,
            )

            if success and self.verbose > 1:
                print(
                    '.   ✅ Record %s inserted in %s.%s'
                    % (
                        column_report_name,
                        dst_schema,
                        dst_main_table,
                    )
                )

            if not success:
                return None

        # Recheck the record ID after inserting the main record.
        if not record_id:
            record_id = self.pg_session_C._Single_search_tab_keys(
                self._Lower_text_values(
                    main_query_D,
                    dst_schema,
                    dst_main_table,
                ),
                ['id'],
                dst_schema,
                dst_main_table,
            )

        if not record_id:
            print(
                '.  ❌ ERROR: could not retrieve record_id after '
                'inserting device model to %s.%s'
                % (dst_schema, dst_main_table)
            )
            return None

        main_table_id = '%s_id' % dst_main_table

        if 'name' in main_query_D:
            name = main_query_D['name']
        else:
            name = 'record %s' % record_id[0]

        services().log(
            section="sql",
            status="info",
            message=_format_trace_message(
                "Managing related PostgreSQL tables",
                {
                    "process": self.process_S.process.process,
                    "main_table": main_table_key,
                    "main_record_id": record_id[0],
                    "related_table_count": len(schema_table_query_D),
                    "related_tables": list(schema_table_query_D.keys()),
                },
            ),
        )

        self._Define_specifics(
            main_query_D,
            record_id,
            schema_table_query_D,
            main_table_id,
            name,
        )

        services().log(
            section="sql",
            status="success",
            message=_format_trace_message(
                "JSON-to-PostgreSQL import completed",
                {
                    "process": self.process_S.process.process,
                    "main_table": main_table_key,
                    "main_record_id": record_id[0],
                },
            ),
        )

    def _Define_specifics(
        self,
        main_query_D,
        record_id,
        schema_table_query_D,
        main_table_id,
        name,
    ):
        '''Define device model specifics.'''

        def Split_arrays():
            updated_query_D = deepcopy(
                schema_table_query_D[schema_table]
            )

            return_bool = False

            for item in schema_table_query_D[schema_table]:
                if item.endswith('_array') and '__' in item:
                    return_bool = True

                    item_parts = item.split('__')

                    if item_parts[0].endswith('_array'):
                        continue

                    the_item = schema_table_query_D[
                        schema_table
                    ][item]

                    value_csv = the_item[
                        the_item.index("{") + 1:
                        the_item.rindex("}")
                    ]

                    value_in_L = value_csv.split(',')

                    updated_query_D.pop(item)

                    new_item = item.removesuffix("_array")

                    for value_in in value_in_L:
                        updated_query_D[new_item] = value_in

                        self._Manage_specifics(
                            updated_query_D,
                            updated_query_D,
                            main_table_id,
                            schema,
                            table,
                            record_id[0],
                            name,
                        )

            return return_bool

        # Manage each related table using the main record ID.
        for schema_table in schema_table_query_D:
            schema_table_query_D[
                schema_table
            ][main_table_id] = record_id[0]

            if self.verbose > 1:
                print(
                    '      Managing specifics in sub schema.table:',
                    schema_table,
                )

            schema, table = schema_table.split('.')

            if (
                len(schema_table_query_D[schema_table]) <= 3
                and next(
                    iter(schema_table_query_D[schema_table])
                ).endswith('_array')
                and '__' in next(
                    iter(schema_table_query_D[schema_table])
                )
            ):
                # Expand array fields into one-to-many records.
                keys = list(
                    schema_table_query_D[schema_table].keys()
                )

                keys.remove(main_table_id)

                new_query_D = {}

                for key in keys:
                    new_query_D[key] = (
                        schema_table_query_D[schema_table][key]
                        .strip("{}")
                        .split(",")
                    )

                for item in range(len(new_query_D[keys[0]])):
                    item_query_D = {
                        main_table_id: schema_table_query_D[
                            schema_table
                        ][main_table_id],
                    }

                    for key in keys:
                        column_alias = (
                            key.split('__')[1]
                            .split('_array')[0]
                            .replace('name', 'id')
                        )

                        column_alias += '__%s' % (
                            column_alias.replace('id', 'name')
                        )

                        item_query_D[column_alias] = (
                            new_query_D[key][item].strip()
                        )

                    self._Define_specifics(
                        main_query_D,
                        record_id,
                        {schema_table: item_query_D},
                        main_table_id,
                        name,
                    )

                continue

            if not Split_arrays():
                self._Manage_specifics(
                    main_query_D,
                    schema_table_query_D[schema_table],
                    main_table_id,
                    schema,
                    table,
                    record_id[0],
                    name,
                )

    def _Manage_specifics(
        self,
        main_query_D,
        updated_query_D,
        main_table_id,
        schema,
        table,
        record_value,
        name,
    ):
        schema_table = '%s.%s' % (schema, table)

        services().log(
            section="sql",
            status="info",
            message=_format_trace_message(
                "Managing related table record",
                {
                    "process": self.process_S.process.process,
                    "schema": schema,
                    "table": table,
                    "record": name,
                    "main_record_id": record_value,
                    "parameter_names": list(updated_query_D.keys()),
                },
            ),
        )

        if schema_table in SPECIAL_SEARCH_TABLES_D:
            at_columns_D = {
                k: v
                for k, v in updated_query_D.items()
                if k.startswith('@')
            }

            retrieve_function = getattr(
                self.pg_ai4sh_C,
                SPECIAL_SEARCH_TABLES_D[schema_table],
            )

            at_params_D = retrieve_function(
                updated_query_D,
                at_columns_D,
                self.pg_session_C,
            )

            if not at_params_D:
                print(
                    '.  ❌ ERROR: could not retrieve @-record '
                    'for %s.%s'
                    % (schema, table)
                )
                return None

            self._Insert_at_records(
                updated_query_D,
                at_params_D,
                schema,
                table,
                main_query_D['provision_id__provision_name'],
            )

            return None

        if table == 'observation_log_method_tier':
            method_tier_L = [
                'field',
                'home',
                'laboratory',
                'drone',
                'satellite',
                'document',
                'senses',
                'auxiliary',
            ]

            for item in method_tier_L:
                updated_query_D[item] = getattr(
                    self.process_S.process.parameters,
                    item,
                )

        test_rec = self.pg_session_C._Single_search_foreign_key(
            updated_query_D,
            [main_table_id],
            schema,
            table,
        )

        services().log(
            section="sql",
            status="success",
            message=_format_trace_message(
                (
                    "Existing related record found"
                    if test_rec
                    else "No existing related record found"
                ),
                {
                    "process": self.process_S.process.process,
                    "schema": schema,
                    "table": table,
                    "record": name,
                    "record_exists": bool(test_rec),
                    "overwrite": self.process_S.process.overwrite,
                    "delete": self.process_S.process.delete,
                },
            ),
        )

        if not test_rec and not self.process_S.process.delete:
            result = self._Insert(
                updated_query_D,
                schema,
                table,
                name,
            )

        elif self.process_S.process.overwrite:
            self._Update(
                updated_query_D,
                schema,
                table,
                name,
            )

        elif self.process_S.process.delete:
            where_statement = '%s = %s' % (
                main_table_id,
                record_value,
            )

            self.pg_session_C._Delete_(
                schema,
                table,
                where_statement,
            )

        else:
            services().log(
                section="sql",
                status="success",
                message=_format_trace_message(
                    "Existing related PostgreSQL record skipped",
                    {
                        "process": self.process_S.process.process,
                        "schema": schema,
                        "table": table,
                        "record": name,
                        "reason": "overwrite is disabled",
                    },
                ),
            )

            if self.process_S.process.verbose > 1:
                print(
                    '.     ✅ Record already registered in table %s, '
                    'use overwrite to update'
                    % table
                )

    def _Insert_at_records(
        self,
        updated_query_D,
        at_params_D,
        schema,
        table,
        provision_name,
    ):
        # Exclude @-prefixed fields from the shared record payload.
        core_query_D = {
            k: v
            for k, v in updated_query_D.items()
            if not k.startswith('@')
        }

        for key in at_params_D:
            sql_query_D = deepcopy(core_query_D)
            sql_query_D.update(at_params_D[key])

            if isinstance(at_params_D[key]['value'], list):
                if not self._Check_provision_array(
                    provision_name,
                    len(at_params_D[key]['value']),
                ):
                    return None

                array_table = '%s_array' % table

                self._Insert(
                    sql_query_D,
                    schema,
                    array_table,
                    'at record',
                )

            else:
                self._Insert(
                    sql_query_D,
                    schema,
                    table,
                    'at record',
                )

    def _Check_provision_array(self, provision_name, value_len):
        record = (
            self.pg_ai4sh_C
            ._Retrieve_wavelength_cardinality_from_provision(
                provision_name,
                self.pg_session_C,
            )
        )

        if not record:
            print(
                '.  ❌ ERROR: could not retrieve wavelength '
                'cardinality for provision %s'
                % provision_name
            )
            return None

        if record != value_len:
            print(
                '.  ❌ ERROR: length of input array does not match '
                'wavelength cardinality for provision %s. '
                'Expected %s values, got %s values.'
                % (provision_name, record, value_len)
            )
            return None

        return True