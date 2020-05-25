from conans import ConanFile, tools
from conans.errors import ConanInvalidConfiguration
import os
import json
import re

class CrashpadConan(ConanFile):
    name = "crashpad"
    version = "20200324"
    description = "Crashpad is a crash-reporting system."
    license = "Apache-2.0"
    homepage = "https://chromium.googlesource.com/crashpad/crashpad"
    url = "https://github.com/bincrafters/conan-crashpad"
    topics = ("conan", "crash-reporting", "logging", "minidump", "crash")
    settings = "os", "compiler", "build_type", "arch"
    options = {'linktime_optimization': [True, False]}
    default_options = {"linktime_optimization": False}
    exports = [ "patches/*", "LICENSE.md" ]
    short_paths = True

    _commit_id = "311a5a2fdd5b6be8cee01b66991933397094204f"
    _source_dir = "crashpad"
    _build_name = "out/Conan"
    _build_dir = os.path.join(_source_dir, _build_name)

    def build_requirements(self):
        self.build_requires("depot_tools_installer/20200515@bincrafters/stable")
        self.build_requires("ninja/1.9.0")

    def _mangle_spec_for_gclient(self, solutions):
        return json.dumps(solutions)          \
                   .replace("\"", "\\\"")     \
                   .replace("false", "False") \
                   .replace("true", "True")

    def _make_spec(self):
        solutions = [{
            "url": "%s@%s" % (self.homepage, self._commit_id),
            "managed": False,
            "name": "%s" % (self.name),
        }]
        return "solutions=%s" % self._mangle_spec_for_gclient(solutions)

    def configure(self):
        # It's not a C project, but libcxx is hardcoded in the project
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def source(self):
        self.run("gclient config --spec=\"%s\"" % self._make_spec(), run_environment=True)
        self.run("gclient sync --no-history", run_environment=True)

        patch_base = os.path.join(self._source_dir, "third_party/mini_chromium/mini_chromium");
        tools.patch(base_path=patch_base,
                    patch_file="patches/buildsystem-adaptions.patch")

    def _get_target_cpu(self):
        arch = str(self.settings.arch)

        if arch == "x86":
            return "x86"
        elif arch == "x86_64":
            return "x64"

        # best effort... please contribute, if you actually tested those platforms
        elif arch.startswith("arm"):
            match = re.match('^armv([0-9]+)', arch)
            if int(match.group(1)) >= 8 and not "32" in arch:
                return "arm64"
            else:
                return "arm"
        elif arch.startswith("mips"):
            return "mipsel"

        raise ConanInvalidConfiguration("your architecture (%s) is not supported" % arch)

    def _set_env_arg(self, args, envvar, gnvar):
        val = os.getenv(envvar)
        if val:
            args += [ "%s=\\\"%s\\\"" % (gnvar, val) ]

    def _setup_args_gn(self):
        args = ["is_debug=%s" % ("true" if self.settings.build_type == "Debug" else "false"),
                "target_cpu=\\\"%s\\\"" % self._get_target_cpu()]

        if self.settings.os == "Macos" and self.settings.get_safe("os.version"):
            args += [ "mac_deployment_target=\\\"%s\\\"" % self.settings.os.version ]
        if self.settings.os == "Windows":
            args += [ "linktime_optimization=%s" % str(self.options.linktime_optimization).lower()]
        if self.settings.os == "Windows" and self.settings.get_safe("compiler.runtime"):
            crt = str(self.settings.compiler.runtime)
            args += [ "dynamic_crt=%s" % ("true" if crt.startswith("MD") else "false") ]

        self._set_env_arg(args, "CC",       "custom_cc")
        self._set_env_arg(args, "CXX",      "custom_cxx")
        self._set_env_arg(args, "CFLAGS",   "extra_cflags_c")
        self._set_env_arg(args, "CFLAGS",   "extra_cflags_objc")
        self._set_env_arg(args, "CXXFLAGS", "extra_cflags_cc")
        self._set_env_arg(args, "CXXFLAGS", "extra_cflags_objcc")
        self._set_env_arg(args, "LDFLAGS",  "extra_ldflags")

        return " ".join(args)

    # This is a workaround for macOS builds where certain linker errors started
    # occuring. Apparently the crashpad build system does not package a few *.o
    # files properly. That leads to missing symbols when linking with 3rd party
    # projects. More details here:
    #
    #  * https://groups.google.com/a/chromium.org/forum/#!topic/crashpad-dev/XVggc7kvlNs
    def _export_mach_utils(self):
        mactools = tools.XCRun(self.settings)
        self.run("%s cr %s %s" %                                      \
            (mactools.ar,                                             \
             os.path.join(self._build_dir, "obj/util/libmachutil.a"), \
             os.path.join(self._build_dir, "obj", self._build_name, "gen/util/mach/*.o")))

    def build(self):
        with tools.chdir(self._source_dir):
            self.run('gn gen %s --args="%s"' % (self._build_name, self._setup_args_gn()), run_environment=True)
            self.run("ninja -j%d -C %s" % (tools.cpu_count(), self._build_name), run_environment=True)

        if self.settings.os == "Macos":
            self._export_mach_utils()

    def _copy_lib(self, src_dir):
        self.copy("*.a", dst="lib",
                  src=os.path.join(self._build_dir, src_dir), keep_path=False)
        self.copy("*.lib", dst="lib",
                  src=os.path.join(self._build_dir, src_dir), keep_path=False)

    def _copy_headers(self, dst_dir, src_dir):
        self.copy("*.h", dst=os.path.join("include", dst_dir),
                         src=os.path.join(self._source_dir, src_dir))

    def _copy_bin(self, src_bin):
        self.copy(src_bin, src=self._build_dir, dst="bin")
        self.copy("%s.exe" % src_bin, src=self._build_dir, dst="bin")

    def package(self):
        self.copy("LICENSE", dst="licenses", src=self._source_dir,
                             ignore_case=True, keep_path=False)

        self._copy_headers("crashpad/client", "client")
        self._copy_headers("crashpad/util",   "util")
        self._copy_headers("mini_chromium",   "third_party/mini_chromium/mini_chromium")
        self._copy_lib("obj/client")
        self._copy_lib("obj/util")
        self._copy_lib("obj/third_party/mini_chromium")
        self._copy_bin("crashpad_handler")

    def package_info(self):
        self.cpp_info.includedirs = [ "include/crashpad", "include/mini_chromium" ]
        self.cpp_info.libdirs = [ "lib" ]
        self.cpp_info.libs = tools.collect_libs(self)

        if self.settings.os == "Macos":
            self.cpp_info.exelinkflags.append("-framework CoreFoundation")
            self.cpp_info.exelinkflags.append("-framework CoreGraphics")
            self.cpp_info.exelinkflags.append("-framework CoreText")
            self.cpp_info.exelinkflags.append("-framework Foundation")
            self.cpp_info.exelinkflags.append("-framework IOKit")
            self.cpp_info.exelinkflags.append("-framework Security")
            self.cpp_info.exelinkflags.append("-lbsm")
            self.cpp_info.sharedlinkflags = self.cpp_info.exelinkflags
