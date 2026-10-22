"""
pg_get_schema_table.py

Retrieve schema and table destinations defined for system processes.

Created on 18 Nov 2021
Updated 4 Jan 2024

@author: thomasgumbricht
"""

import json

from app.services.workspace_context import services


def _format_trace_message(message, details):
    """Preserve legacy details inside the current trace message."""
    return (
        f"{message} | "
        f"{json.dumps(details, ensure_ascii=False, default=str)}"
    )


class Get_schema_table:
    """Retrieve schema/table mappings for the current process."""

    def __init__(self):
        pass

    def _Get_process_schema_table(self):
        """
        Map schema.table destinations to their process parameters.

        Read the current structured process parameters and retrieve
        the destinations registered for that process.
        """
        process_id = self.process_S.process.process

        services().log(
            section="sql",
            status="info",
            message=_format_trace_message(
                "Resolving process schema and table mapping",
                {
                    "process": process_id,
                },
            ),
        )

        try:
            schema_table_query_D = {}

            # Collect parameter names from the structured process.
            parameter_L = []

            for parameter_id in (
                self.process_S.process.parameters.__dict__
            ):
                parameter_L.append(parameter_id)

            value_L = []

            for item in parameter_L:
                value_L.append(
                    getattr(self.process_S.process.parameters, item)
                )

            parameter_value_D = dict(zip(parameter_L, value_L))

            services().log(
                section="process",
                status="success",
                message=_format_trace_message(
                    "Process parameters collected for schema mapping",
                    {
                        "process": process_id,
                        "parameter_count": len(parameter_value_D),
                    },
                ),
            )

            # Retrieve distinct destinations registered for this process.
            sql = (
                "SELECT DISTINCT in_schema, in_table "
                "FROM process.process_parameter_schema_table "
                "WHERE process = %s;"
            )

            records = self.pg_session_C._Execute_search_all_sql(
                sql,
                (process_id,),
            )

            services().log(
                section="sql",
                status="success",
                message=_format_trace_message(
                    "Schema and table destinations retrieved",
                    {
                        "process": process_id,
                        "destination_count": len(records),
                    },
                ),
            )

            for record in records:
                schema_table = "%s.%s" % (
                    record[0],
                    record[1],
                )
                schema_table_query_D[schema_table] = {}

                services().log(
                    section="sql",
                    status="info",
                    message=_format_trace_message(
                        "Mapping parameters to schema and table destination",
                        {
                            "process": process_id,
                            "schema_table": schema_table,
                        },
                    ),
                )

                # Retrieve parameters registered for this destination.
                sql = (
                    "SELECT parameter "
                    "FROM process.process_parameter_schema_table "
                    "WHERE process = %s "
                    "AND in_schema = %s AND in_table = %s;"
                )

                recs = self.pg_session_C._Execute_search_all_sql(
                    sql,
                    (process_id, record[0], record[1]),
                )

                destination_parameters = {
                    item[0]
                    for item in recs
                }

                for key in list(parameter_value_D):
                    if key in destination_parameters:
                        schema_table_query_D[schema_table][key] = (
                            parameter_value_D[key]
                        )

                # Expand free parameters registered through the @% marker.
                if "@%" in schema_table_query_D[schema_table]:
                    for key in list(parameter_value_D):
                        if key.startswith("@%") and len(key) > 2:
                            schema_table_query_D[schema_table][key] = (
                                parameter_value_D[key]
                            )

                    schema_table_query_D[schema_table].pop("@%")
                    parameter_value_D.pop("@%")

                # Expand free parameters registered through the @ marker.
                if "@" in schema_table_query_D[schema_table]:
                    for key in list(parameter_value_D):
                        if key.startswith("@") and len(key) > 1:
                            schema_table_query_D[schema_table][key] = (
                                parameter_value_D[key]
                            )

                    schema_table_query_D[schema_table].pop("@")
                    parameter_value_D.pop("@")

                services().log(
                    section="sql",
                    status="success",
                    message=_format_trace_message(
                        "Parameters mapped to schema and table destination",
                        {
                            "process": process_id,
                            "schema_table": schema_table,
                            "parameter_count": len(
                                schema_table_query_D[schema_table]
                            ),
                        },
                    ),
                )

            services().log(
                section="sql",
                status="success",
                message=_format_trace_message(
                    "Process schema and table mapping completed",
                    {
                        "process": process_id,
                        "destination_count": len(schema_table_query_D),
                        "mapped_parameter_count": sum(
                            len(parameters)
                            for parameters in schema_table_query_D.values()
                        ),
                    },
                ),
            )

            return schema_table_query_D

        except Exception as exc:
            services().log(
                section="sql",
                status="error",
                message=_format_trace_message(
                    "Process schema and table mapping failed",
                    {
                        "process": process_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                ),
            )

            raise