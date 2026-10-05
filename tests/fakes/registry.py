from agent_builder.core.schemas import ModelConfig


class FakeRegistry:
    """In-memory Registry with one builder model and one agent model."""

    def __init__(self):
        self.records = []
        self.runs = []
        self.orchestrators = []
        self.tools = []
        self.models = {
            "builder-model": ModelConfig(
                id="builder-model",
                model="azure/builder",
                api_key="builder-secret",
                api_base="https://example.openai.azure.com",
            ),
            "agent-model": ModelConfig(
                id="agent-model",
                model="azure/agent",
                api_key="agent-secret",
                api_base="https://example.openai.azure.com",
            ),
        }

    def save(self, record):
        self.records.append(record)
        return record

    def get(self, name, version=None):
        matches = [record for record in self.records if record.spec.name == name]
        if version is not None:
            matches = [record for record in matches if record.version == version]
        return matches[-1] if matches else None

    def list(self):
        return self.records

    def next_version(self, name):
        record = self.get(name)
        return record.version + 1 if record else 1

    def save_model(self, model):
        self.models[model.id] = model
        return model

    def get_model(self, model_id):
        return self.models.get(model_id)

    def list_models(self):
        return list(self.models.values())

    def save_run(self, run):
        self.runs.append(run)
        return run

    def get_run(self, run_id):
        return next((run for run in self.runs if run.run_id == run_id), None)

    def list_runs(self, target=None, limit=20):
        return [run for run in self.runs if target in (None, run.target)][:limit]

    def save_orchestrator(self, record):
        self.orchestrators = [
            o for o in self.orchestrators
            if (o.spec.name, o.version) != (record.spec.name, record.version)
        ] + [record]
        return record

    def get_orchestrator(self, name, version=None, status="approved"):
        matches = [
            o for o in self.orchestrators
            if o.spec.name == name and version in (None, o.version) and status in (None, o.status)
        ]
        return max(matches, key=lambda o: o.version, default=None)

    def list_orchestrators(self):
        return self.orchestrators

    def save_tool(self, record):
        self.tools.append(record)
        return record

    def get_tool(self, name, version=None):
        matches = [t for t in self.tools if t.spec.name == name and version in (None, t.version)]
        return max(matches, key=lambda t: t.version, default=None)

    def list_tools(self):
        return self.tools

    def set_tool_status(self, name, version, status):
        self.get_tool(name, version).status = status
