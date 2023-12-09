# rsdb-merge
Merge some of the RSDB file types from TOTK

Supported RSDB files:
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
- Tag.Product
- XLinkPropertyTableList.Product

## Usage

For each mod containing RSDB files, use this command to generate json changelogs:

`rsdb-merge.exe --generate-changelog "PATH_TO_RSDB_FOLDER" --output "path to where to generate the changelog"`

After generating a changelog, rename it to anything you want, like "ModName_RSDB.json" (to avoid it getting overwritten when generating another one).

Once you have all json changelogs from each of your mods containing RSDB edits, place them all in the same folder (preferably a new empty folder) and use this command:

`rsdb-merge.exe --apply-changelogs "PATH_TO_FOLDER_CONTAINING_JSONS" --output "PATH_TO_WHERE_YOU_WANT_RSDB_FILES_GENERATED" --version 121`

This second command will use all json changelogs to merge the edits and generate RSDB files for version 1.2.1 in the output folder you choose (you can change `--version 121` to generate merged RSDB files for any version you want)

The priority works with the alphanumerical order of the json changelogs' file names. So for example if a.json and b.json both edit the same blocks of data, the edit from b.json will overwrite it (this is only for blocks that are edited and not blocks that are added).

## Help
```
usage: rsdb-merge.exe [-h] [--generate-changelog GENERATE_CHANGELOG]
                      [--apply-changelogs APPLY_CHANGELOGS]
                      [--output OUTPUT] [--version VERSION]

Generate and apply changelogs for RSDB

options:
  -h, --help            show this help message and exit
  --generate-changelog GENERATE_CHANGELOG
                        Path to the folder containing .byml.zs files to
                        generate changelogs.
  --apply-changelogs APPLY_CHANGELOGS
                        Path to the folder containing .json changelogs to
                        apply.
  --output OUTPUT       Path to the output directory for the generated
                        changelog or for the generated RSDB files.
  --version VERSION     Version of TOTK for which to generate RSDB files (example: 121)
```

## Special thanks

- Thanks to [Arch Leaders](https://github.com/ArchLeaders) for [byml-to-yaml](https://github.com/ArchLeaders/byml_to_yaml/)
- Thanks to [MediaMoots](https://github.com/MediaMoots) for [Tag.Product-Tool](https://github.com/MediaMoots/Tag.Product-Tool)
