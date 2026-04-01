from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # 阿里云百炼配置
    DASHSCOPE_API_KEY: str = ""
    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_model: str = "glm-5"

    # MCP Server配置
    mcp_server_url: str = "http://localhost:8001/mcp"

    # 服务配置
    backend_port: int = 8002

settings = Settings()