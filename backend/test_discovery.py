from pathlib import Path

from app.services.discovery_service import discovery_service


# ==========================================================
# CHANGE THIS PATH
# ==========================================================
# Replace <UPLOAD_ID> with the UUID created by your ZIP upload.
#
# Example:
# app/uploads/extracted/9f8fd2ec-9d6e-4e19-9293-295acd8d21b9
#
TEST_DIRECTORY = Path(
    "app/uploads/extracted/c38d8005-2f4d-4cb8-a679-d6d9d863de2f"
)


def main() -> None:
    """
    Independently test the TalentAI DiscoveryService.
    """

    print("\n" + "=" * 70)
    print("TalentAI - Module 3 File Discovery Test")
    print("=" * 70)

    # ------------------------------------------------------
    # 1. Verify directory exists
    # ------------------------------------------------------

    if not TEST_DIRECTORY.exists():
        print("\nERROR:")
        print(
            f"Directory not found:\n{TEST_DIRECTORY}"
        )
        return

    if not TEST_DIRECTORY.is_dir():
        print("\nERROR:")
        print(
            f"Path is not a directory:\n{TEST_DIRECTORY}"
        )
        return

    print(
        f"\nScanning:\n{TEST_DIRECTORY.resolve()}"
    )

    # ------------------------------------------------------
    # 2. Run DiscoveryService
    # ------------------------------------------------------

    discovered_files = (
        discovery_service.discover_files(
            extraction_directory=str(
                TEST_DIRECTORY
            )
        )
    )

    # ------------------------------------------------------
    # 3. Display discovered files
    # ------------------------------------------------------

    print(
        f"\nTotal supported files discovered: "
        f"{len(discovered_files)}"
    )

    print("\n" + "-" * 70)

    for index, discovered_file in enumerate(
        discovered_files,
        start=1,
    ):

        print(f"\nFILE {index}")

        print(
            f"Filename       : "
            f"{discovered_file.filename}"
        )

        print(
            f"Extension      : "
            f"{discovered_file.file_extension}"
        )

        print(
            f"Relative Path  : "
            f"{discovered_file.relative_path}"
        )

        print(
            f"Source Folder  : "
            f"{discovered_file.source_folder}"
        )

        print(
            f"Folder Chain   : "
            f"{discovered_file.folder_chain}"
        )

        print(
            f"Folder Depth   : "
            f"{discovered_file.folder_depth}"
        )

        print(
            f"Root Level     : "
            f"{discovered_file.is_root_level}"
        )

        print("-" * 70)

    print(
        "\nDiscovery test completed."
    )


if __name__ == "__main__":
    main()
