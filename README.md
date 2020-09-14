[![ko-fi](https://img.shields.io/badge/Support%20me%20on-Ko--fi-FF5E5B.svg?logo=ko-fi&style=flat-square)](https://ko-fi.com/mastercoms)
[![Liberapay](https://img.shields.io/liberapay/receives/mastercoms.svg?logo=liberapay&style=flat-square)](https://liberapay.com/mastercoms/)
[![Steam donate](https://img.shields.io/badge/Donate%20via-Steam-00adee.svg?style=flat-square&logo=steam)](https://steamcommunity.com/tradeoffer/new/?partner=85845165&token=M9cQHh8N)
[![Join the Discord chat](https://img.shields.io/badge/Discord-%23comtress--client-7289da.svg?style=flat-square&logo=discord)](https://discord.gg/CuPb2zV)


# Team Comtress 2

Team Fortress 2, but with a lot of fixes, quality of life improvements and performance optimizations!

## About

What is Team Comtress 2? It's a version of Team Fortress 2, based on the recent leak which aims to fix many bugs, performance issues, etc. Imagine it like mastercomfig on steroids!

Obviously, as a leaked build, it's not useful for getting better performance in Casual on its own (you can't use this build to connect to any existing servers), but it can help me a lot if you all can test it, so that I am more confident in sending many of these changes to Valve for them to include in the base game! Please let me know how it works for you!

## Install

1. [Download](https://github.com/mastercomfig/team-comtress-2/releases/latest) the latest release.
2. Copy your current `Team Fortress 2` installation to a new folder.
3. Extract the ZIP download to this new folder.
4. Make sure you don't have any configs installed.
5. Double click `start_tf2.bat`. Note that you must have Steam running.
6. Enjoy!

## New console commands and launch options

Although configs are not recommended (use video options to customize), there are some new customization variables you can try that haven't been added yet!

**Console commands/variables:**

* `tf_taunt_first_person_enable`: Forces first person taunts
* `tf_viewmodels_offset_override`: Unlocked from base TF2, format is x y z
* `tf_disable_weapon_skins`: Disables skins
* `tf_skip_halloween_bomb_hat_translucency`: Halloween bomb hat will disappear if spy cloaks, instead of turning translucent along with cloak
* `r_skybox_lowend`: Use low quality skybox textures only meant for DX8
* `tf_hud_target_id_disable`: Disable searching for a player to show the target ID for
* `tf_viewmodel_alpha`: Controls how translucent viewmodels are (1-255)
* `dsp_off`: Unlocked from base TF2, disables sound positional effects
* `cl_ragdoll_disable`: Disables all corpse effects (gibs, disintegration, ragdolls)
* `tf_fx_blood`: Controls blood splatter effects
* `fx_drawimpactdebris`, `fx_drawimpactdust`, `fx_drawmetalspark`: Unlocked from base TF2, controls bullet impact dust
* `cl_hud_playerclass_playermodel_lod`: Controls LOD for the player model preview in the HUD
* `g_ragdoll_fadespeed`, `g_ragdoll_lvfadespeed`: Controls how fast ragdolls fade (lv is for low violence mode)
* `cl_particle_retire_cost`: Unlocked from base TF2, set to `0.0001` to force lower quality particles
* `r_force_fastpath 1`: Forces shader fast paths for higher GPU performance.
* `tf_weaponspread_continuous_seed`: If set to >-1, the base seed for fixed recoil spread for continuo
us single bullet fire weapons.
* `tf_weaponspread_continuous_seed_multishot`: If set to >-1, the base seed for fixed recoil spread for continuous multi-bullet fire weapons like the Minigun.

**Launch options:**

* `-particle_fallback`: 2 uses DX8 particles, 1 uses lowend DX9 particles, 0 uses default.

## Build

**DISCLAIMER:** If you are not a developer, building the game from source is not what you want. Use the pre-built [Releases](https://github.com/mastercomfig/team-comtress-2/releases). Also, building this on Mac/Linux, while possible, is not covered here. Please let us know if you get it to work!

### Building
1. Get [Visual Studio 2019 Community Edition](https://visualstudio.microsoft.com/vs/) for building TF2. The required installation components are: "Desktop development with C++" and the "C++ MFC for latest v142 build tools (x86 & x64)".
2. Clone this repo
3. Open `/thirdparty/protobuf-2.5.0/vsprojects/libprotobuf.vcproj`
4. Run both the Debug and the Release builds
5. Run `regedit` and [add an association for the latest VS](https://github.com/ValveSoftware/source-sdk-2013/issues/72#issuecomment-326633328) (add a key at `HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\10.0\Projects\{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}`, add a `String` property named `DefaultProjectExtension`, set the value to `vcproj`)
6. Set the [environment variable](https://superuser.com/a/985947) `VALVE_NO_AUTO_P4` to `true` and `PreferredToolArchitecture` to `x64`.
7. Run `/creategameprojects_dev.bat`
8. Open `/games.sln`
9. Build the VS project
10. The executables are placed at `../game/hl2.exe` for the client and at `../game/srcds.exe` for the server. Note: this path is outside the repository.

### Running and Debugging
1. For the compiled binaries to run, you will need to copy your current TF2 installation to `../game` (relative to your repostiory, outside of it).
1. You will also need all the usual game resources (same as when installing a pre-built release). Feel free to skip `.sound.cache` files, but otherwise just merge all the depots into `../game`. Once again, do not override any files that VS put in `../game/bin`
1. To setup debugging, in Visual Studio, select `launcher_main` as the startup project, then go to its `Properties->Configuration Properties->Debugging`. Set `Command` to your `../game/hl2.exe` binary, the `Command Arguments` to `-steam -game tf -insecure -novid -nojoy -nosteamcontroller -nohltv -particles 1 -noborder -particle_fallback 2 -dev -allowdebug` and `Working Directory` to your game installation folder i.e. `../game/bin`. Note: all the paths here are relative to your copy of the repository (same place where `games.sln` is located), do **not** set these values verbatim.
1. For the server, follow the same procedures but choose the `Dedicated_main` project and set the `Command` to `../game/srcds.exe`. The suggested server launch options are `-game tf -console -nomaster -insecure +sv_pure 0 +maxplayers 32 +sv_lan 1 -dev -allowdebug`.

NOTE: Team Comtress 2 is no longer compatible with mastercomfig. Please do not use mastercomfig or any other TF2 config.

See [the Valve dev wiki page](https://developer.valvesoftware.com/wiki/Installing_and_Debugging_the_Source_Code) for another explanation of the last two steps.

Other launch options to consider:
- `sw` to force windowed mode
- `-w WIDTH -h HEIGHT` to set the resolution
- `+map MAPNAME` to automatically launch a map on startup

## Build System Info

### Configuration Separation
To ensure that Release and Debug builds do not conflict, we replaced the default `$LIBPUBLIC` macro with two: `$LIBPUBLICDEBUG` and `$LIBPUBLICRELEASE`. Same for libraries that get generated into `$LIBCOMMON`. This means that most builds will not work by default since they need `$LIBPUBLIC` to be defined. This includes the `$Lib` and `$ImpLib` VPC commands. Fixing this involves going through all the occurances of `$LIBPUBLIC` and `$LIBCOMMON` (if it is a generated library and not imported one) and replacing them with two `$File` commands (one for debug and one for release) with `$ExcludedFromBuild "Yes"` in the configuration for the opposite configuration (i.e. for `$LIBPUBLICDEBUG` set `$ExcludedFromBuild` in the `"Release"` configuration).

Since this is extremely non-trivial,
```
$Macro ARGLIBNAME library_name
$Include "$SRCDIR\vpc_scripts\lib_include.vpc"
```
will do it for you for the `library_name` library.

A similar script for `$LIBCOMMON` libraries is `$SRCDIR\vpc_scripts\lib_common_include.vpc`

### Published DLL Tracking
In Valve's build scripts, the runtime DLL dependencies are implicit, so if a required DLL is missing or needs a rebuild, it will not be picked up by the build system. Fixing this invovles adding project dependencies with
```
$Macro ARGPROJNAME proj_name
$Include "$SRCDIR\vpc_scripts\proj_include.vpc"
```

To find which projects you need, run the `/clean_bins.sh` script (MinGW or Cygwin required) to clean out the published binaries and cause the game to print errors whenever a dependency is missing. Add each of these dependencies and the builds should work.

To avoid going through a VPC re-run and a VS rebuild that follows for the core project, build the dependencies manually first and check if any others are needed before adding them to the VPC. This saves a lot of time.

### PyVPC
A WIP Python port of the Valve VPC tool is included under `/pyvpc/`. I have only tested it from under Cygwin, under which Python gets very confused regarding which platform it is running on, so some hacks were necessary. It should probably still work under native Windows. It currently has a hard dependcy on the [`colorful`](https://github.com/timofurrer/colorful) module.

The plan for this tool is to have a way of parsing the original Valve VPC files, then applying patches to the generated configurations from a Python script, then using that representation to generate `.vcproj` files. Or we might juse use the Valve configurations as a base to manually write Python build definitions.

In any case, the processing of the VPC files is there for greater compatibility with potential future leaks/working with other code based on VPC.

We do not want to use VPC ultimately, since it depends on a large amount of Valve code (its own version of tier0, vstdlib, and more) and because patching C tools is a pain. And we do want to patch it because of the various bugs and inflexibilities in VPC which make some things outright impossible/not work, and others extremely complicated (see the two sections above). The patch for clean build configuration separation alone touched 71 files and required more than 1000 changes.

## Legal

Valve, the Valve logo, Steam, the Steam logo, Team Fortress, the Team Fortress logo, Source, the Source logo are trademarks and/or registered trademarks of Valve Corporation in the U.S. and/or other countries.

Team Comtress 2 is not sponsored, endorsed, licensed by, or affiliated with Valve Corporation.

See license for details.
