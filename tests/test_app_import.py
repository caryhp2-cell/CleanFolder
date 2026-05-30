def test_app_entrypoint_imports():
    from offline_npu_renamer.app import main

    assert callable(main)
