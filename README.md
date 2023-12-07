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

## Help
```
usage: rsdb-merge.exe [-h] --file1 FILE1 --file2 FILE2

Merge two .byml.zs files (RSDB only)

options:
  -h, --help     show this help message and exit
  --file1 FILE1  Path to the first .byml.zs file.
  --file2 FILE2  Path to the second .byml.zs file.
```
