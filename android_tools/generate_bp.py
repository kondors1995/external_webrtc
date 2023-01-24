#!/usr/bin/env python

import json
import sys

PRINT_ORIGINAL_FULL = False

def FormatList(l):
    return json.dumps(list(l))

def IsInclude(name):
    return name.endswith('.h') or name.endswith('.inc')

def FilterIncludes(l):
    return filter(lambda x: not IsInclude(x), l)

def PrintOrigin(target):
    print('/* From target:')
    if PRINT_ORIGINAL_FULL:
        print(json.dumps(target, sort_keys = True, indent = 4))
    else:
        print(target['original_name'])
    print('*/')

def MakeRelatives(l):
    return map(lambda x: x.split('//').pop(), l)

def FormatName(name):
    return 'webrtc_' + name.split('/').pop().replace(':', '__')

def FormatNames(target):
    target['original_name'] = target['name']
    target['name'] = FormatName(target['name'])
    target['deps'] = [FormatName(d) for d in target['deps']]
    target['sources'] = list(map(lambda s: (':' + FormatName(s[1:])) if s.startswith(':') else s, target['sources']))
    return target

def FilterFlags(flags, to_skip = set()):
    skipped_opts = set([
        '-Wall',
        '-Werror',
        '-L',
        '-isystem',
        '-Xclang',
        '-B',
        '--sysroot',
        '-fcrash-diagnostics-dir',
        '.',
        '-fdebug-compilation-dir',
        '-instcombine-lower-dbg-declare=0',
        '-Wno-non-c-typedef-for-linkage',
        '-Werror',
        '-fcomplete-member-pointers',
        '-fno-stack-protector',
        '--target=i686-linux-android16',
        '--target=aarch64-linux-android21'
        '--target=i686-linux-android16',
        '--target=x86_64-linux-android21',
        '--target=arm-linux-androideabi16',
        '-m64',
        '-m32',
        '-march=x86-64',
        '-march=armv8-a',
        '-mllvm',
        '-target-feature',
        '+crypto',
        '+crc',
        '-fno-unique-section-names',
        '-fno-short-enums',
        '-fno-delete-null-pointer-checks',
        '-ffile-compilation-dir=.',
        '-Wno-unneeded-internal-declaration',
        '-Wno-unreachable-code-aggressive',
        '-Wno-unreachable-code-break',
        '-fuse-ctor-homing',
        '-fno-rtti',
        '-gsplit-dwarf', # TODO(b/266468464): breaks riscv
        ]).union(to_skip)
    return [x for x in flags if not any([x.startswith(y) for y in skipped_opts])]

def PrintHeader():
    print('package {')
    print('    default_applicable_licenses: ["external_webrtc_license"],')
    print('}')
    print('')
    print('// Added automatically by a large-scale-change that took the approach of')
    print('// \'apply every license found to every target\'. While this makes sure we respect')
    print('// every license restriction, it may not be entirely correct.')
    print('//')
    print('// e.g. GPL in an MIT project might only apply to the contrib/ directory.')
    print('//')
    print('// Please consider splitting the single license below into multiple licenses,')
    print('// taking care not to lose any license_kind information, and overriding the')
    print('// default license using the \'licenses: [...]\' property on targets as needed.')
    print('//')
    print('// For unused files, consider creating a \'fileGroup\' with "//visibility:private"')
    print('// to attach the license to, and including a comment whether the files may be')
    print('// used in the current project.')
    print('//')
    print('// large-scale-change included anything that looked like it might be a license')
    print('// text as a license_text. e.g. LICENSE, NOTICE, COPYING etc.')
    print('//')
    print('// Please consider removing redundant or irrelevant files from \'license_text:\'.')
    print('// See: http://go/android-license-faq')
    print('')
    print('///////////////////////////////////////////////////////////////////////////////')
    print('// Do not edit this file directly, it\'s automatically generated by a script. //')
    print('// Modify android_tools/generate_android_bp.py and run that instead.         //')
    print('///////////////////////////////////////////////////////////////////////////////')
    print('')
    print('license {')
    print('    name: "external_webrtc_license",')
    print('    visibility: [":__subpackages__"],')
    print('    license_kinds: [')
    print('        "SPDX-license-identifier-Apache-2.0",')
    print('        "SPDX-license-identifier-BSD",')
    print('        "SPDX-license-identifier-MIT",')
    print('        "SPDX-license-identifier-Zlib",')
    print('        "legacy_notice",')
    print('        "legacy_unencumbered",')
    print('    ],')
    print('    license_text: [')
    print('        "LICENSE",')
    print('        "PATENTS",')
    print('        "license_template.txt",')
    print('    ],')
    print('}')

def GatherDefaultFlags(targets):
    default = {
            'cflags' : [],
            'cflags_c' : [],
            'cflags_cc' : [],
            'asmflags' : [],
    }
    arch = {
            'x64': {},
            'x86': {},
            'arm64': {},
            'arm': {},
    }

    first = True
    for target in targets.values():
        typ = target['type']
        if typ != 'static_library':
            continue
        if first:
            first = False
            # Add all the flags to the default, we'll remove some later
            for flag_type in default.keys():
                default[flag_type] = []
                for flag in target[flag_type]:
                    default[flag_type].append(flag)
                for a in arch.keys():
                    arch[a][flag_type] = []
                    for flag in target.get('arch', {}).get(a, {}).get(flag_type, []):
                        arch[a][flag_type].append(flag)
        else:
            for flag_type in default.keys():
                if flag_type not in target:
                    target[flag_type] = []
                default[flag_type] = list(set(default[flag_type]) & set(target[flag_type]))
                for a in arch.keys():
                    arch[a][flag_type] = list(set(arch[a][flag_type]) | set(target.get('arch', {}).get(a, {}).get(flag_type, [])))

    default['arch'] = arch
    return default

def GenerateDefault(targets):
    in_default = GatherDefaultFlags(targets)
    print('cc_defaults {')
    print('    name: "webrtc_defaults",')
    print('    local_include_dirs: [')
    print('      ".",')
    print('      "webrtc",')
    print('      "third_party/crc32c/src/include",')
    print('    ],')
    if PRINT_ORIGINAL_FULL:
        for typ in in_default.keys():
            print('    // {0}: ['.format(typ.replace('asmflags', 'asflags')
                .replace('cflags_cc', 'cppflags')
                .replace('cflags_c', 'conlyflags')))
            for flag in FilterFlags(in_default[typ]):
                print('        // "{0}",'.format(flag.replace('"', '\\"')))
            print('    // ],')
    selected_cflags = [
        '-Wno-everything',
        '-Wno-all',
        '-Wno-error',
        '-Wno-unreachable-code-aggressive',
        '-Wno-unreachable-code-break',
        '-Wno-unused-parameter',
        '-Wno-missing-field-initializers',
        '-Wno-implicit-const-int-float-conversion',
        '-DUSE_UDEV',
        '-DUSE_AURA=1',
        '-DUSE_GLIB=1',
        '-DUSE_NSS_CERTS=1',
        '-DUSE_X11=1',
        '-D_FILE_OFFSET_BITS=64',
        '-D_LARGEFILE_SOURCE',
        '-D_LARGEFILE64_SOURCE',
        '-D_GNU_SOURCE',
        '-DWEBRTC_ENABLE_PROTOBUF=0',
        '-DWEBRTC_ANDROID_PLATFORM_BUILD=1',
        '-DWEBRTC_INCLUDE_INTERNAL_AUDIO_DEVICE',
        '-DRTC_ENABLE_VP9',
        '-DWEBRTC_HAVE_SCTP',
        '-DWEBRTC_LIBRARY_IMPL',
        '-DWEBRTC_NON_STATIC_TRACE_EVENT_HANDLERS=1',
        '-DWEBRTC_POSIX',
        '-DWEBRTC_LINUX',
        '-DWEBRTC_STRICT_FIELD_TRIALS=0',
        '-DWEBRTC_ENABLE_AVX2',
        '-DABSL_ALLOCATOR_NOTHROW=1',
        '-DWEBRTC_APM_DEBUG_DUMP=0',
        '-msse3',
        ]
    selected_cflags_x86 = ['-mavx2', '-mfma', '-DHAVE_ARM64_CRC32C=0']
    selected_cflags_x64 = ['-msse2', '-mavx2', '-mfma', '-DHAVE_ARM64_CRC32C=0']
    selected_cflags_arm = ['-DWEBRTC_HAS_NEON', '-DWEBRTC_ARCH_ARM_V7', '-DWEBRTC_ARCH_ARM', '-mfpu=neon', '-mthumb', '-DHAVE_ARM64_CRC32C=0']
    selected_cflags_arm64 = ['-DWEBRTC_HAS_NEON', '-DWEBRTC_ARCH_ARM64', '-DHAVE_ARM64_CRC32C=0']
    print('    cflags: {0},'.format(FormatList(selected_cflags)))
    print('    header_libs: [')
    print('      "libwebrtc_absl_headers",')
    print('    ],')
    print('    static_libs: [')
    print('        "libaom",')
    print('        "libevent",')
    print('        "libopus",')
    print('        "libsrtp2",')
    print('        "libvpx",')
    print('        "libyuv",')
    print('        "libpffft",')
    print('        "rnnoise_rnn_vad",')
    print('    ],')
    print('    shared_libs: [')
    print('        "libcrypto",')
    print('        "libprotobuf-cpp-full",')
    print('        "libprotobuf-cpp-lite",')
    print('        "libssl",')
    print('    ],')
    print('    host_supported: true,')
    print('    // vendor needed for libpreprocessing effects.')
    print('    vendor: true,')
    print('    target: {')
    print('        darwin: {')
    print('            enabled: false,')
    print('        },')
    print('    },')
    print('    arch: {')
    print('        x86: {')
    print('            cflags: {0}'.format(FormatList(selected_cflags_x86)))
    print('        },')
    print('        x86_64: {')
    print('            cflags: {0}'.format(FormatList(selected_cflags_x64)))
    print('        },')
    print('        arm: {')
    print('            cflags: {0}'.format(FormatList(selected_cflags_arm)))
    print('        },')
    print('        arm64: {')
    print('            cflags: {0}'.format(FormatList(selected_cflags_arm64)))
    print('        },')
    print('    },')
    print('    visibility: [')
    print('        "//frameworks/av/media/libeffects/preprocessing:__subpackages__",')
    print('        "//device/google/cuttlefish/host/frontend/webrtc:__subpackages__",')
    print('    ],')
    print('}')
    in_default['cflags'].extend(selected_cflags)
    in_default['arch']['x86']['cflags'].extend(selected_cflags_x86)
    in_default['arch']['x64']['cflags'].extend(selected_cflags_x64)
    in_default['arch']['arm']['cflags'].extend(selected_cflags_arm)
    in_default['arch']['arm64']['cflags'].extend(selected_cflags_arm64)

    # The flags in the default entry can be safely removed from the targets
    for target in targets.values():
        flag_types = in_default.keys() - {'arch'}
        for flag_type in flag_types:
            target[flag_type] = FilterFlags(target.get(flag_type, []), in_default[flag_type])
            if len(target[flag_type]) == 0:
                target.pop(flag_type)
            if 'arch' not in target:
                continue
            for arch_name in in_default['arch'].keys():
                if arch_name not in target['arch']:
                    continue
                arch = target['arch'][arch_name]
                if flag_type not in arch:
                    continue
                arch[flag_type] = FilterFlags(arch[flag_type], in_default['arch'][arch_name][flag_type])
                if len(arch[flag_type]) == 0:
                    arch.pop(flag_type)
                    if len(arch.keys()) == 0:
                        target['arch'].pop(arch_name)
            if len(target['arch'].keys()) == 0:
                target.pop('arch')

    return in_default

def TransitiveDependencies(name, dep_type, targets):
    target = targets[name]
    field = 'transitive_' + dep_type
    if field in target.keys():
        return target[field]
    target[field] = set()
    if target['type'] == dep_type:
        target[field].add(name)
    for d in target.get('deps', []):
        if targets[d]['type'] == dep_type:
            target[field].add(d)
        target[field] |= TransitiveDependencies(d, dep_type, targets)
    return target[field]

def GenerateGroup(target):
    # PrintOrigin(target)
    pass

def GenerateSourceSet(target):
    sources = target.get('sources', [])
    # arch is not defined for filegroups so put all the sources in the top level,
    # the static libraries that depend on the filegroup will add it in the
    # appropriate arch.
    for arch in target.get('arch', {}).values():
        sources += arch.get('sources', [])
    if len(sources) == 0:
        return ''
    PrintOrigin(target)

    name = target['name']
    print('filegroup {')
    print('    name: "{0}",'.format(name))
    print('    srcs: {0},'.format(FormatList(sources)))
    print('}')
    return name

def GenerateStaticLib(target, targets):
    PrintOrigin(target)
    name = target['name']
    print('cc_library_static {')
    print('    name: "{0}",'.format(name))
    print('    defaults: ["webrtc_defaults"],')
    sources = target.get('sources', [])
    print('    srcs: {0},'.format(FormatList(sources)))
    print('    host_supported: true,')
    if 'asmflags' in target.keys():
        asmflags = target['asmflags']
        if len(asmflags) > 0:
            print('    asflags: {0},'.format(FormatList(asmflags)))
    if 'cflags' in target.keys():
        cflags = target['cflags']
        print('    cflags: {0},'.format(FormatList(cflags)))
    if 'cflags_c' in target.keys():
        cflags_c = target['cflags_c']
        if len(cflags_c) > 0:
            print('    conlyflags: {0},'.format(FormatList(cflags_c)))
    if 'cflags_cc' in target.keys():
        cflags_cc = target['cflags_cc']
        if len(cflags_cc) > 0:
            print('    cppflags: {0},'.format(FormatList(cflags_cc)))
    static_libs = [d for d in target.get('deps', []) if targets[d]['type'] == 'static_library']
    if len(static_libs) > 0:
        print('    static_libs: {0},'.format(FormatList(static_libs)))
    if 'arch' in target:
        print('   arch: {')
        arch_map = {'x86': 'x86','x64': 'x86_64','arm': 'arm','arm64': 'arm64'}
        for arch_name, arch in target['arch'].items():
            print('       ' + arch_map[arch_name] + ': {')
            if 'cflags' in arch.keys():
                cflags = arch['cflags']
                print('            cflags: {0},'.format(FormatList(cflags)))
            if 'cflags_c' in arch.keys():
                cflags_c = arch['cflags_c']
                if len(cflags_c) > 0:
                    print('            conlyflags: {0},'.format(FormatList(cflags_c)))
            if 'cflags_cc' in arch.keys():
                cflags_cc = arch['cflags_cc']
                if len(cflags_cc) > 0:
                    print('            cppflags: {0},'.format(FormatList(cflags_cc)))
            if 'deps' in arch:
                  static_libs = [d for d in arch['deps'] if targets[d]['type'] == 'static_library']
                  print('            static_libs: {0},'.format(FormatList(static_libs)))
            if 'sources' in arch:
                  sources = arch['sources']
                  print('            srcs: {0},'.format(FormatList(sources)))
            if 'enabled' in arch:
                print('            enabled: {0},'.format(arch['enabled']))
            print('        },')
        print('   },')
    print('}')
    return name

def DFS(seed, targets):
    visited = set()
    stack = [seed]
    while len(stack) > 0:
        nxt = stack.pop()
        if nxt in visited:
            continue
        visited.add(nxt)
        stack += targets[nxt]['deps']
        stack += [s[1:] for s in targets[nxt]['sources'] if s.startswith(':')]
        if 'arch' not in targets[nxt]:
            continue
        for arch in targets[nxt]['arch']:
            if 'deps' in arch:
                stack += arch['deps']
            if 'sources' in arch:
                stack += [s[1:] for s in arch['sources'] if s.startswith(':')]
    return visited

def Preprocess(project):
    targets = {}
    for name, target in project['targets'].items():
        target['name'] = name
        targets[name] = target
        if target['type'] == 'shared_library':
            # Don't bother creating shared libraries
            target['type'] = 'static_library'
        if 'defines' in target:
            target['cflags'] = target.get('cflags', []) + ['-D{0}'.format(d) for d in target['defines']]
            target.pop('defines')
        if 'sources' not in target:
            continue
        sources = list(MakeRelatives(FilterIncludes(target['sources'])))
        if len(sources) > 0:
            target['sources'] = sources
        else:
            target.pop('sources')

    # These dependencies are provided by aosp
    ignored_targets = {
            '//third_party/libaom:libaom',
            '//third_party/libevent:libevent',
            '//third_party/opus:opus',
            '//third_party/libsrtp:libsrtp',
            '//third_party/libvpx:libvpx',
            '//third_party/libyuv:libyuv',
            '//third_party/pffft:pffft',
            '//third_party/rnnoise:rnn_vad',
            '//third_party/boringssl:boringssl',
            '//third_party/android_ndk:cpu_features',
            '//buildtools/third_party/libunwind:libunwind',
            '//buildtools/third_party/libc++:libc++',
        }
    for name, target in targets.items():
        # Skip all "action" targets
        if target['type'] in {'action', 'action_foreach'}:
            ignored_targets.add(name)
    targets = {name: target for name, target in targets.items() if name not in ignored_targets}

    for target in targets.values():
        # Don't depend on ignored targets
        target['deps'] = [d for d in target['deps'] if d not in ignored_targets]

    # filegroups can't have dependencies, so put their dependencies in the static libraries that
    # depend on them.
    for target in targets.values():
        if target['type'] == 'static_library':
            source_sets = TransitiveDependencies(target['name'], 'source_set', targets)
            source_sets_deps = set()
            for ss in source_sets:
                source_sets_deps |= set(targets[ss]['deps'])
            target['deps'] = list(set(target['deps']) | source_sets | source_sets_deps)

    # Ignore empty source sets
    empty_sets = set()
    for name, target in targets.items():
        if target['type'] == 'source_set' and 'sources' not in target:
            empty_sets.add(name)
    for s in empty_sets:
        targets.pop(s)
    for target in targets.values():
        target['deps'] = [d for d in target['deps'] if d not in empty_sets]

    # Move source_set dependencies to the sources fields of static libs
    for target in targets.values():
        if 'sources' not in target:
            target['sources'] = []
        if target['type'] != 'static_library':
            continue
        source_sets = {d for d in target['deps'] if targets[d]['type'] == 'source_set'}
        target['deps'] = list(set(target['deps']) - source_sets)
        target['sources'] += [':' + ss for ss in source_sets]
        if 'arch' in target:
            for arch in target.values():
                if 'deps' in arch:
                    source_sets = {d for d in arch['deps'] if targets[d]['type'] == 'source_set'}
                    if len(source_sets) == 0:
                        continue;
                    arch['deps'] = list(set(arch['deps']) - source_sets)
                    arch['sources'] = arch.get('sources', []) + [':' + ss for ss in source_sets]

    # Select libwebrtc, libaudio_processing and its dependencies
    selected = set()
    selected |= DFS('//:webrtc', targets)
    selected |= DFS('//modules/audio_processing:audio_processing', targets)
    return {FormatName(n): FormatNames(targets[n]) for n in selected}

def NonNoneFrom(*args):
    for a in args:
        if a is not None:
            return a
    return None

def MergeListField(target, f, x64_target, x86_target, arm64_target, arm_target):
    x64_set = set(x64_target.get(f, []))
    x86_set = set(x86_target.get(f, []))
    arm64_set = set(arm64_target.get(f, []))
    arm_set = set(arm_target.get(f, []))

    common = x64_set & x86_set & arm64_set & arm_set
    x64_only = x64_set - common
    x86_only = x86_set - common
    arm64_only = arm64_set - common
    arm_only = arm_set - common

    if len(common) > 0:
        target[f] = list(common)
    if len(x64_only) > 0:
        target['arch']['x64'][f] = list(x64_only)
    if len(x86_only) > 0:
        target['arch']['x86'][f] = list(x86_only)
    if len(arm64_only) > 0:
        target['arch']['arm64'][f] = list(arm64_only)
    if len(arm_only) > 0:
        target['arch']['arm'][f] = list(arm_only)

def Merge(x64_target, x86_target, arm64_target, arm_target):
    # The new target shouldn't have the transitive dependencies memoization fields
    # or have the union of those fields from all 4 input targets.
    target = {}
    for f in ['original_name', 'name', 'type']:
        target[f] = NonNoneFrom(x64_target.get(f),
                                x86_target.get(f),
                                arm64_target.get(f),
                                arm_target.get(f))

    target['arch'] = {'x64': {}, 'x86': {}, 'arm64': {}, 'arm': {}}
    if x64_target is None:
        target['arch']['x64']['enabled'] = 'false'
    if x86_target is None:
        target['arch']['x86']['enabled'] = 'false'
    if arm64_target is None:
        target['arch']['arm64']['enabled'] = 'false'
    if arm_target is None:
        target['arch']['arm']['enabled'] = 'false'

    list_fields = ['sources',
                   'deps',
                   'cflags',
                   'cflags_c',
                   'cflags_cc',
                   'asmflags']
    for lf in list_fields:
        MergeListField(target, lf, x64_target, x86_target, arm64_target, arm_target)

    # Static libraries should be depended on at the root level and disabled for
    # the corresponding architectures.
    for arch in target['arch'].values():
        if 'deps' not in arch:
            continue
        deps = arch['deps']
        if 'deps' not in target:
            target['deps'] = []
        target['deps'] += deps
        arch.pop('deps')

    # Remove empty sets
    if len(target['arch']['x64']) == 0:
        target['arch'].pop('x64')
    if len(target['arch']['x86']) == 0:
        target['arch'].pop('x86')
    if len(target['arch']['arm64']) == 0:
        target['arch'].pop('arm64')
    if len(target['arch']['arm']) == 0:
        target['arch'].pop('arm')
    if len(target['arch']) == 0:
        target.pop('arch')

    return target

def MergeAll(x64_targets, x86_targets, arm64_targets, arm_targets):
    names = x64_targets.keys() | x86_targets.keys() | arm64_targets.keys() | arm_targets.keys()
    targets = {}
    for name in names:
        targets[name] = Merge(x64_targets.get(name, {}),
                              x86_targets.get(name, {}),
                              arm64_targets.get(name, {}),
                              arm_targets.get(name, {}))
    return targets

if len(sys.argv) != 5:
    print('wrong number of arguments')
    exit()

x64_json_file = open(sys.argv[1], 'r')
x64_targets = Preprocess(json.load(x64_json_file))

x86_json_file = open(sys.argv[2], 'r')
x86_targets = Preprocess(json.load(x86_json_file))

arm64_json_file = open(sys.argv[3], 'r')
arm64_targets = Preprocess(json.load(arm64_json_file))

arm_json_file = open(sys.argv[4], 'r')
arm_targets = Preprocess(json.load(arm_json_file))

targets = MergeAll(x64_targets, x86_targets, arm64_targets, arm_targets)

PrintHeader()

GenerateDefault(targets)
print('\n\n')

for target in targets.values():
    typ = target['type']
    if typ == 'static_library':
        GenerateStaticLib(target, targets)
    elif typ == 'source_set':
        GenerateSourceSet(target)
    elif typ == 'group':
        GenerateGroup(target)
    else:
        print('Unknown type: {0} ({1})'.format(typ, target['name']), file = sys.stderr)
        exit(1)
    print('\n\n')

webrtc_libs = [d for d in TransitiveDependencies(FormatName('//:webrtc'), 'static_library', targets)]
print('cc_library_static {')
print('    name: "libwebrtc",')
print('    defaults: ["webrtc_defaults"],')
print('    export_include_dirs: ["."],')
print('    whole_static_libs: {0},'.format(FormatList(webrtc_libs + ['libpffft', 'rnnoise_rnn_vad'])))
print('}')

print('\n\n')

audio_proc_libs = [d for d in TransitiveDependencies(FormatName('//modules/audio_processing:audio_processing'), 'static_library', targets)]
print('cc_library_static {')
print('    name: "webrtc_audio_processing",')
print('    defaults: ["webrtc_defaults"],')
print('    export_include_dirs: [')
print('        ".",')
print('        "modules/include",')
print('        "modules/audio_processing/include",')
print('    ],')
print('    whole_static_libs: {0},'.format(FormatList(audio_proc_libs + ['libpffft', 'rnnoise_rnn_vad'])))
print('}')
