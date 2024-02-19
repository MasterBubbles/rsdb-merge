# rsdb-merge [![Downloads](https://img.shields.io/github/downloads/MasterBubbles/rsdb-merge/total)](https://github.com/MasterBubbles/rsdb-merge/releases)
This tool can merge all RSDB file types from TOTK (the files located in `romfs\RSDB`).<br>Mods that contain such a folder are typically standalone weapons or armors.

<img src="https://raw.githubusercontent.com/MasterBubbles/rsdb-merge/master/images/screenshot.png">

## For merging mods

As an end user, you only require one thing, it's the merge function. You do not need to generate or apply changelogs, the merge function does everything for you. 

It can be done in 2 different ways, either you use the user interface, select the TotK version you are using, browse to the folder containing all your mods, and click the merge button

Or if you fancy some scripting and prefer the command line, you can do it this way:

`rsdb-merge.exe --merge "%AppData%\Ryujinx\mods\contents\0100f2c0115b6000" --version 121`

This example includes the Ryujinx mod folder path for TotK, so if using something else replace the path to the actual directory containing all your mods.

Of course, the `--version` argument has to match the TotK version that you are using (eg: 121 for version 1.2.1).

This will create a new mod in your mod directory called `00_MERGED_RSDB`. As emulators load mods in alphanumerical order, the 00_ prefix ensures that it takes higher priority over all other mods. If you need to merge mods again in the future, delete that folder first.

Merging the RSDB folder most of the time will not be sufficient, as the Mals folder edits also need to be merged. You can use [ArchLeader](https://github.com/ArchLeaders)'s tool called [MalsMerger](https://github.com/ArchLeaders/MalsMerger) for this (it requires a RomFS dump of the game, which can be done either with the nxdumptool rewrite homebrew, or if using an emulator simply by right clicking the game and clicking on the option to extract the romfs).

Resource table entries also need to be recalculated after merging RSDB and Mals. Please use the [RESTBL calculator](https://gamebanana.com/tools/15857) to do so.

## Development Usage

For modders who want to take their edits from RSDB files and apply that to all versions of TotK, use this command to generate a json changelog:

`rsdb-merge.exe --generate-changelog "PATH_TO_RSDB_FOLDER" --output "path to where to generate the changelog"`

After generating a changelog, you can rename it to anything you want, like "ModName_RSDB.json" (to avoid it getting overwritten when generating another one).

The changelogs can also be useful if you want to figure out what a mod edits, and if you want to reverse engineer what was done on a mod to make your own.

You can generate multiple json changelogs if needed to merge multiple mods (but I recommend using the other option described earlier for merging). Place them all in the same folder (preferably a new empty folder) and use this command:

`rsdb-merge.exe --apply-changelogs "C:\PATH\TO\FOLDER_CONTAINING_JSON(S)" --output "C:\PATH\TO\WHERE_YOU_WANT_RSDB_FILES_GENERATED" --version 121`

This second command will use all json changelogs to merge the edits and generate RSDB files for version 1.2.1 in the output folder you choose (you can change `--version 121` to generate merged RSDB files for any version you want). It is also possible to have only one changelog in the folder (in the eventuality that you want to port a mod from one version to another).

The priority works with the alphanumerical order of the json changelogs' file names. So for example if a.json and b.json both edit the same blocks of data, the edit from b.json will overwrite it (this is only for blocks that are edited and not blocks that are added).

Additionally, you have the option of using an array of paths for applying changelogs. For example, if you have several mod folders that each contain a rsdb.json changelog, you can use multiple folder paths separated with this line character: `|` :

`rsdb-merge.exe --apply-changelogs "C:\path\to\mod1|C:\path\to\mod2|C:\path\to\mod3" --output "C:\PATH\TO\WHERE_YOU_WANT_RSDB_FILES_GENERATED" --version 121`

## CLI Help
```
usage: rsdb-merge.exe [-h] [--version VERSION] [--merge MERGE]
                      [--generate-changelog GENERATE_CHANGELOG]
                      [--apply-changelogs APPLY_CHANGELOGS] [--output OUTPUT]

Generate and apply changelogs for RSDB

options:
  -h, --help            show this help message and exit
  --version VERSION     Version of TOTK for which to generate RSDB files
                        (example: 121).
  --merge MERGE         Path to the folder containing all of your mods
  --generate-changelog GENERATE_CHANGELOG
                        Path to the folder containing .byml.zs files to
                        generate a changelog.
  --apply-changelogs APPLY_CHANGELOGS
                        Paths to the folders containing .json changelogs to
                        apply.
  --output OUTPUT       Path to the output directory for the generated
                        changelog or for the generated RSDB files.
```

## Special thanks

- Thanks to [Arch Leaders](https://github.com/ArchLeaders) for [byml-to-yaml](https://github.com/ArchLeaders/byml_to_yaml/)
- Thanks to [MediaMoots](https://github.com/MediaMoots) for [Tag.Product-Tool](https://github.com/MediaMoots/Tag.Product-Tool)
