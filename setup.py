import argparse
import os
import subprocess
import sys

from Cython.Build import cythonize
from setuptools import setup, Extension


def get_args():
    this_dir = os.path.dirname(__file__)
    default_srilm_dir = os.path.join(this_dir, "../")

    parser = argparse.ArgumentParser()
    parser.add_argument("--srilm-option", default="")
    parser.add_argument("--srilm", default=default_srilm_dir, help="Location of SRILM directory")
    parser.add_argument("--lbfgs", default=None, help="Location of liblbfgs directory")
    args, copy_args = parser.parse_known_args()
    return args, copy_args


def main():
    args, copy_args = get_args()
    modules = get_modules(args)
    try:
        setup(
            name="srilm",
            version="3.0.0",
            description="Python binding for SRI Language Modeling Toolkit implemented in Cython",
            author="Yi Su",
            author_email="nuance1979@hotmail.com",
            license="MIT",
            packages=["srilm"],
            ext_package="srilm",
            ext_modules=cythonize(modules, annotate=True, language_level="3"),
            script_args=copy_args,
        )
    except Exception as e:
        if "liblbfgs" in e.message:
            raise AttributeError("Build failed, maybe try specifying the location of --liblbfgs?")
        else:
            raise


def get_machine_type(args):
    # Pip does a pre-install probe for egg_info and doesn't supply --install-options. We have to fake it on that call.
    if "egg_info" in sys.argv:
        return "i686-m64"

    machine_type_file = os.path.join(args.srilm, "sbin/machine-type")
    if not os.path.isfile(machine_type_file):
        raise FileNotFoundError(
            "SRILM does not seem to be in location {}\n\t(cannot find {})".format(args.srilm, machine_type_file)
        )

    machine_type = (
        subprocess.check_output(["/bin/bash", os.path.join(args.srilm, "sbin/machine-type")])
        .strip()
        .decode("ascii")
    )
    return machine_type


def get_modules(args):
    machine_type = get_machine_type(args)

    lib_path = machine_type + args.srilm_option

    lib_dirs = [os.path.join(args.srilm, "lib", lib_path)]
    include_dirs = [
        os.path.join(args.srilm),
        os.path.join(args.srilm, "include"),
    ]
    compile_args = None
    link_args = None
    if machine_type == "i686-m64":
        compile_args = ["-fopenmp"]
        link_args = ["-fopenmp"]
    elif machine_type == "macosx":
        lib_dirs.extend(["/usr/lib", "/usr/local/lib"])

    if args.lbfgs:
        include_dirs.append(os.path.join(args.lbfgs))
        lib_dirs.append(os.path.join(args.lbfgs, "lib"))

    compact_def_macros = [("USE_SARRAY", 1), ("USE_SARRAY_TRIE", 1), ("USE_SARRAY_MAP2", 1)]
    if args.srilm_option == "_c":
        def_macros = compact_def_macros
    elif args.srilm_option == "_s":
        def_macros = compact_def_macros + [("USE_SHORT_VOCAB", 1), ("USE_XCOUNTS", 1)]
    elif args.srilm_option == "_l":
        def_macros = compact_def_macros + [("USE_LONGLONG_COUNTS", 1), ("USE_XCOUNTS", 1)]
    else:
        def_macros = []

    module_dict = {
        "vocab": ["srilm/vocab.pyx"],
        "stats": ["srilm/stats.pyx"],
        "discount": ["srilm/discount.pyx"],
        "base": ["srilm/base.pyx"],
        "ngram": ["srilm/ngram.pyx"],
        "maxent": ["srilm/maxent.pyx"],
        "utils": ["srilm/utils.pyx"],
    }

    modules = []
    for n, s in module_dict.items():
        modules.append(
            Extension(
                name=n,
                sources=s,
                language="c++",
                define_macros=[("HAVE_ZOPEN", "1")] + def_macros,
                include_dirs=include_dirs,
                libraries=["lbfgs", "iconv"],
                library_dirs=lib_dirs,
                extra_compile_args=compile_args,
                extra_link_args=link_args,
                extra_objects=[
                    os.path.join(args.srilm, "lib", lib_path, "liboolm.a"),
                    os.path.join(args.srilm, "lib", lib_path, "libdstruct.a"),
                    os.path.join(args.srilm, "lib", lib_path, "libmisc.a"),
                    os.path.join(args.srilm, "lib", lib_path, "libz.a"),
                ],
                cython_directives={"embedsignature": True},
            )
        )
    return modules


if __name__ == '__main__':
    main()
