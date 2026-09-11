import json

import pytest

from ops.release.release_deployment_transaction import DeploymentError, execute_env_transaction


def test_env_transaction_restores_actual_image_after_failure(tmp_path):
    (tmp_path / ".env").write_text("IMAGE_TAG=old\n", encoding="utf-8")
    (tmp_path / "actual-images.json").write_text(json.dumps({"backend": "old"}), encoding="utf-8")

    with pytest.raises(DeploymentError, match="DEPLOYMENT_FAILED"):
        execute_env_transaction(
            tmp_path,
            new_env="IMAGE_TAG=new\n",
            new_images={"backend": "new"},
            apply=lambda: None,
            verify=lambda: (_ for _ in ()).throw(RuntimeError("health failed")),
        )

    assert (tmp_path / ".env").read_text(encoding="utf-8") == "IMAGE_TAG=old\n"
    assert json.loads((tmp_path / "actual-images.json").read_text(encoding="utf-8")) == {"backend": "old"}
    assert not (tmp_path / ".env.next").exists()
