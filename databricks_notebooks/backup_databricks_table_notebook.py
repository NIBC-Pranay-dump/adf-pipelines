# Databricks notebook source
"""This script is used to backup all tables in a Databricks catalog to an external location.

Grants required:
- Write files / read files on external location
"""

from datetime import datetime, timezone


def _get_tables(catalog_name: str) -> list:
    """Get all tables in a catalog.

    We want to skip all the views from each catalog and only back up the managed
    and external tables.

    Args:
        catalog_name (str): The catalog name.

    Returns:
        list: A list of table names in the catalog.

    """
    tables = spark.sql(
        f"SELECT table_schema, table_name FROM {catalog_name}.information_schema.tables WHERE table_type != 'VIEW'"
    ).collect()

    print(tables)

    full_table_paths = [
        f"{catalog_name}.{tuple(row)[0]}.{tuple(row)[1]}" for row in tables
    ]

    print(f"Tables in catalog `{catalog_name}`: {full_table_paths}")

    return full_table_paths


def _generate_table_paths(table_names: list[str]) -> dict[str, dict[str, str]]:
    """Generate the input and output table paths.

    Args:
        table_names (list[str]): A list of table names to backup

    Returns:
        dict[str, dict[str, str]]: A dictionary of table names and their input and output paths.
            example:
            {
                "table_name": {
                    "input_table": "input_catalog.input_schema.input_table",
                    "backup_table": "full_output_path_including_external_location"
                }
            }

    """
    # use timestamp as part of the backup folder
    backup_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"Backup timestamp: {backup_timestamp}")

    # crete the input table paths directly from storage account
    table_paths = {
        table_name: {
            "input_table": table_name,
            "backup_table": f"{backup_to_location_path}/databricks/{backup_timestamp}/{table_name}",
        }
        for table_name in table_names
    }

    print(f"The following tables will be backed up: {table_paths}")

    return table_paths


def _backup_data(input_table_name: str, output_table_path: str) -> None:
    """Backup a table in Databricks to an external location."""
    # Use writing to parquet instead of clone, as cloning is not supported
    # on tables with column masking
    df_to_back_up = spark.table(input_table_name)
    df_to_back_up.write.format("parquet").mode("overwrite").save(output_table_path)

    print(
        f"Table `{input_table_name}` has been successfully backed up to "
        f"`{output_table_path}`."
    )


def main(catalog_name: str, backup_to_location_path: str) -> None:
    """Backup a table in Databricks to an external location.

    Args:
        catalog_name (str): The catalog name.
        backup_to_location_path (str): The external location path where the table will be backed up.

    """

    print(
        f"Backup specification: catalog_name: `{catalog_name}`, "
        f"backup to location path: `{backup_to_location_path}`."
    )
    input_table_name = _get_tables(catalog_name)

    tables_paths = _generate_table_paths(input_table_name)

    for idx, (_, paths) in enumerate(tables_paths.items()):
        print(f"Backing up datable {idx + 1} of {len(tables_paths)}")

        _backup_data(paths["input_table"], paths["backup_table"])

    print(f"Backup of catalog `{catalog_name}` completed.")


if __name__ == "__main__":
    catalog_name = dbutils.widgets.get("catalog_name")
    backup_to_location_path = dbutils.widgets.get("backup_location")

    main(catalog_name=catalog_name, backup_to_location_path=backup_to_location_path)
