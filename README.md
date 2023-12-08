# rsdb-merge
Merge some of the RSDB file types from TOTK

Currently untested

"Supported" RSDB files (maybe? please test and let me know):
- ActorInfo.Product
- AttachmentActorInfo.Product
- Challenge.Product
- EnhancementMaterialInfo.Product
- EventPlayEnvSetting.Product
- EventSetting.Product
- GameActorInfo.Product
- GameAnalyzedEventInfo.Product
- GameEventBaseSetting.Product
- GameEventMetadata.Product
- LocatorData.Product
- PouchActorInfo.Product
- XLinkPropertyTableList.Product

## Usage

For each mod containing RSDB files, use this command to generate json changelogs:

`rsdb-merge.exe --generate-changelog "PATH_TO_RSDB_FOLDER" --output "path to where to generate the changelog"`

You can rename the changelog to anything you want, like "ModName_RSDB.json"

Once you have all json changelogs from each of your mods containing RSDB edits, place them all in the same folder and use this command:

`rsdb-merge.exe --apply-changelogs "PATH_TO_FOLDER_CONTAINING_JSONS" --output "path to where to generate RSDB files" --version 121`

This second command will generate RSDB files for version 1.2.1 (you can change `--version 121` to whatever version you want)

## Help
```
usage: rsdb-merge.exe [-h] [--generate-changelog GENERATE_CHANGELOG] [--output OUTPUT]
                      [--apply-changelogs APPLY_CHANGELOGS] [--version VERSION]

Generate and apply changelogs for RSDB

options:
  -h, --help            show this help message and exit
  --generate-changelog GENERATE_CHANGELOG
                        Path to the folder containing .byml.zs files to generate changelogs.
  --output OUTPUT       Output path for the generated changelog or for the generated RSDB files.
  --apply-changelogs APPLY_CHANGELOGS
                        Path to the folder containing .json changelogs to apply.
  --version VERSION     Version of the master file to use as a base.
```
