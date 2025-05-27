"""
agent.memory.augment
"""

from pygptprompt.function.factory import FunctionFactory
from pygptprompt.function.sqlite import SQLiteMemoryFunction
from pygptprompt.model.base import ChatModel

from agent.gui.config import ConfigurationManager

episodic_function_definitions = [
    {
        "name": "SQLiteMemoryFunction_get_all_keys",
        "description": "Retrieve all the keys from the memory records in the database.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "SQLiteMemoryFunction_query_memory",
        "description": "Query a memory record with a given key from the database.",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
    {
        "name": "SQLiteMemoryFunction_update_memory",
        "description": "Update or create a memory record with a given key and content in the database.",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}, "content": {"type": "string"}},
            "required": ["key", "content"],
        },
    },
    {
        "name": "SQLiteMemoryFunction_delete_memory",
        "description": "Delete a memory record with a given key from the database.",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
]


class AugmentedMemoryManager:
    def __init__(
        self,
        function_factory: FunctionFactory,
        config: ConfigurationManager,
        chat_model: ChatModel,
    ):
        self.function_factory = function_factory
        self.config = config
        self.chat_model = chat_model

    def _register_sqlite_memory(self, table_name: str) -> None:
        self.function_factory.register_class(
            "SQLiteMemoryFunction",
            SQLiteMemoryFunction,
            table_name=table_name,
            config=self.config,
        )
        self.function_factory.map_class_methods(
            "SQLiteMemoryFunction",
            ["get_all_keys", "query_memory", "update_memory", "delete_memory"],
        )

    def register_episodic_functions(self) -> bool:
        functions = self.config.get_value("function.definitions", [])
        functions.extend(episodic_function_definitions)
        return self.config.set_value("function.definitions", functions)
