from agent_builder.cli import agents


def test_list_agents_reports_empty_registry(monkeypatch, capsys):
    class EmptyRegistry:
        def list(self):
            return []

    monkeypatch.setattr(agents, "get_registry", lambda: EmptyRegistry())

    agents.list_agents()

    assert capsys.readouterr().out.strip() == "No agents found."
