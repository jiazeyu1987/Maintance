from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_TEMPLATE = ROOT / "ops" / "deploy" / "int-ruoyi-test" / "docker-compose.yml"


def test_backend_runtime_points_invoice_voucher_print_assistant_to_target_server() -> None:
    compose = COMPOSE_TEMPLATE.read_text(encoding="utf-8")

    assert "--yudao.erp.invoice-voucher-print-assistant.assistant-host=${SERVER_HOST}" in compose
    assert "--yudao.erp.invoice-voucher-print-assistant.assistant-port=18733" in compose
    assert "invoice-voucher-print-assistant.assistant-port=18734" not in compose
