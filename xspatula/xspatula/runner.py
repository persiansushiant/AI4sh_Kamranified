"""
Public Xspatula workflow runner for the AI4SH application.

Delegate workflow execution to the existing project functions and
send trace messages to the currently bound workspace runtime.
"""

from __future__ import annotations

import sys
from os import getcwd, path
from typing import Any


def _add_project_root_to_python_path() -> str:
    """
    Add the project root to the Python import path.

    Preserve the existing compatibility behavior: resolve the root
    two directories above the current working directory.
    """
    project_root = path.abspath(
        path.join(getcwd(), "../..")
    )

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    return project_root


_add_project_root_to_python_path()


from app.services.workspace_context import services
from src.ai4sh import Run_process
from src.lib import Initiate_process


class Xspatula:
    """
    Configure and run an Xspatula workflow.

    Methods must execute within a bound workspace context.
    Configuration methods return self to support method chaining.
    """

    def __init__(
        self,
        notebook_path: str | None = None,
    ) -> None:
        self.notebook_path = notebook_path or getcwd()

        self.scheme_file: str | None = None
        self.workflow_file: str | None = None
        self.workflow_type: str | None = None

    def set_scheme(self, scheme_file: str) -> Xspatula:
        """Validate and store the scheme JSON path."""
        services().log(
            section="scheme",
            status="info",
            message=(
                "Setting scheme file"
                f" | scheme_file={scheme_file}"
            ),
        )

        try:
            validated_file = self._validate_path_value(
                value=scheme_file,
                field_name="scheme_file",
            )

            self.scheme_file = validated_file

        except Exception as error:
            services().log(
                section="scheme",
                status="error",
                message=(
                    "Scheme file could not be set"
                    f" | scheme_file={scheme_file}"
                    f" | error_type={type(error).__name__}"
                    f" | error={error}"
                ),
            )

            # Preserve the original exception and traceback.
            raise

        services().log(
            section="scheme",
            status="success",
            message=(
                "Scheme file set"
                f" | scheme_file={self.scheme_file}"
            ),
        )

        return self

    def set_job(self, job_file: str) -> Xspatula:
        """Select a job JSON file."""
        return self._set_workflow(
            workflow_file=job_file,
            workflow_type="job",
        )

    def set_pilot(self, pilot_file: str) -> Xspatula:
        """Select a pilot file."""
        return self._set_workflow(
            workflow_file=pilot_file,
            workflow_type="pilot",
        )

    def set_process(self, process_file: str) -> Xspatula:
        """Select a process JSON file."""
        return self._set_workflow(
            workflow_file=process_file,
            workflow_type="process",
        )

    def run(self) -> Any:
        """
        Initialize and execute the selected workflow.

        Preserve the existing behavior: return None when initialization
        produces no processes, and re-raise execution exceptions.
        """
        self._validate_ready_to_run()

        workflow_type = self.workflow_type
        workflow_file = self.workflow_file

        services().log(
            section=workflow_type,
            status="info",
            message=(
                "Starting workflow"
                f" | scheme_file={self.scheme_file}"
                f" | workflow_file={workflow_file}"
                f" | notebook_path={self.notebook_path}"
            ),
        )

        try:
            structured_processes, scheme_parameters = Initiate_process(
                self.notebook_path,
                self.scheme_file,
                workflow_file,
            )

            if structured_processes is None:
                services().log(
                    section=workflow_type,
                    status="error",
                    message=(
                        "Workflow initialization returned no processes"
                        f" | scheme_file={self.scheme_file}"
                        f" | workflow_file={workflow_file}"
                    ),
                )

                return None

            result = Run_process(
                structured_processes,
                scheme_parameters,
            )

        except Exception as error:
            services().log(
                section=workflow_type,
                status="error",
                message=(
                    "Workflow failed"
                    f" | scheme_file={self.scheme_file}"
                    f" | workflow_file={workflow_file}"
                    f" | error_type={type(error).__name__}"
                    f" | error={error}"
                ),
            )

            raise

        services().log(
            section=workflow_type,
            status="success",
            message=(
                "Workflow completed"
                f" | scheme_file={self.scheme_file}"
                f" | workflow_file={workflow_file}"
            ),
        )

        return result

    def _set_workflow(
        self,
        workflow_file: str,
        workflow_type: str,
    ) -> Xspatula:
        """
        Validate the path before updating the selected workflow.

        A validation failure leaves the previous selection unchanged.
        """
        services().log(
            section=workflow_type,
            status="info",
            message=(
                f"Setting {workflow_type} file"
                f" | workflow_file={workflow_file}"
            ),
        )

        try:
            validated_file = self._validate_path_value(
                value=workflow_file,
                field_name=f"{workflow_type}_file",
            )

            self.workflow_file = validated_file
            self.workflow_type = workflow_type

        except Exception as error:
            services().log(
                section=workflow_type,
                status="error",
                message=(
                    f"{workflow_type.capitalize()} file could not be set"
                    f" | workflow_file={workflow_file}"
                    f" | error_type={type(error).__name__}"
                    f" | error={error}"
                ),
            )

            raise

        services().log(
            section=workflow_type,
            status="success",
            message=(
                f"{workflow_type.capitalize()} file set"
                f" | workflow_file={validated_file}"
            ),
        )

        return self

    def _validate_ready_to_run(self) -> None:
        """Require a scheme and a selected workflow before execution."""
        if self.scheme_file is None:
            raise ValueError(
                "A scheme file must be set before running Xspatula."
            )

        if self.workflow_file is None:
            raise ValueError(
                "A job, pilot, or process file must be set before running "
                "Xspatula."
            )

        if self.workflow_type is None:
            raise ValueError(
                "The workflow type is missing."
            )

    @staticmethod
    def _validate_path_value(
        value: str,
        field_name: str,
    ) -> str:
        """
        Validate a path string without accessing the filesystem.

        This checks the value's type and content, not file existence.
        """
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string."
            )

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized_value