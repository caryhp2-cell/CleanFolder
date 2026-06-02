import sys


def test_app_entrypoint_imports():
    from offline_npu_renamer.app import main

    assert callable(main)


def test_app_import_does_not_load_genai_runtime():
    sys.modules.pop("openvino_genai", None)

    import offline_npu_renamer.app  # noqa: F401

    assert "openvino_genai" not in sys.modules
