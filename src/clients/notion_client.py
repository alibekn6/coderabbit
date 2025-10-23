from notion_client import AsyncClient
from src.core.config import settings


class NotionClient:
    def __init__(self):
        self.client = AsyncClient(auth=settings.NOTION_API_KEY)

    async def test_connection(self):
        """Test connection by querying a database"""
        response = await self.client.databases.query(
            database_id=settings.NOTION_DATABASE_ID
        )
        return response

    async def query_database(
        self,
        database_id: str,
        filter_params: dict = None,
        sorts: list = None,
        **kwargs
    ):
        """
        Query a Notion database with optional filters, sorts, and pagination

        Args:
            database_id: The ID of the database to query
            filter_params: Optional filter object
            sorts: Optional list of sort objects
            **kwargs: Additional parameters like page_size, start_cursor
        """
        query_params = {}
        if filter_params:
            query_params["filter"] = filter_params
        if sorts:
            query_params["sorts"] = sorts

        # Add any additional parameters (page_size, start_cursor, etc.)
        query_params.update(kwargs)

        response = await self.client.databases.query(
            database_id=database_id,
            **query_params
        )
        return response

    async def get_database(self, database_id: str):
        """Retrieve a database object"""
        response = await self.client.databases.retrieve(database_id=database_id)
        return response

    async def get_page(self, page_id: str):
        """Retrieve a page object"""
        response = await self.client.pages.retrieve(page_id=page_id)
        return response

    async def retrieve_block_children(self, block_id: str):
        """Retrieve all children blocks from a page or block"""
        blocks = []
        has_more = True
        start_cursor = None

        while has_more:
            response = await self.client.blocks.children.list(
                block_id=block_id,
                start_cursor=start_cursor
            )
            blocks.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

        return blocks

    @staticmethod
    def get_plain_text_from_rich_text(rich_text):
        """Extract plain text from rich text array"""
        return "".join([t.get("plain_text", "") for t in rich_text])

    @staticmethod
    def get_media_source_text(block):
        """Get source URL and caption from media blocks"""
        block_type = block["type"]
        block_data = block[block_type]
        
        # Get source URL
        if "external" in block_data and block_data["external"]:
            source = block_data["external"]["url"]
        elif "file" in block_data and block_data["file"]:
            source = block_data["file"]["url"]
        elif "url" in block_data:
            source = block_data["url"]
        else:
            source = f"[Missing case for media block types]: {block_type}"
        
        # Get caption if exists
        if block_data.get("caption") and len(block_data["caption"]) > 0:
            caption = NotionClient.get_plain_text_from_rich_text(block_data["caption"])
            return f"{caption}: {source}"
        
        return source

    @staticmethod
    def get_text_from_block(block):
        """Extract plain text from any block type"""
        block_type = block["type"]
        block_data = block[block_type]
        text = ""

        # Get rich text from blocks that support it
        if "rich_text" in block_data:
            text = NotionClient.get_plain_text_from_rich_text(block_data["rich_text"])
        # Get text for block types that don't have rich text
        else:
            match block_type:
                case "unsupported":
                    text = "[Unsupported block type]"
                case "bookmark":
                    text = block_data["url"]
                case "child_database":
                    text = block_data["title"]
                case "child_page":
                    text = block_data["title"]
                case "embed" | "video" | "file" | "image" | "pdf":
                    text = NotionClient.get_media_source_text(block)
                case "equation":
                    text = block_data["expression"]
                case "link_preview":
                    text = block_data["url"]
                case "synced_block":
                    if block_data.get("synced_from"):
                        synced_type = block_data["synced_from"]["type"]
                        synced_id = block_data["synced_from"][synced_type]
                        text = f"This block is synced with a block with the following ID: {synced_id}"
                    else:
                        text = "Source sync block that another blocked is synced with."
                case "table":
                    text = f"Table width: {block_data['table_width']}"
                case "table_of_contents":
                    text = f"ToC color: {block_data['color']}"
                case "breadcrumb" | "column_list" | "divider":
                    text = "No text available"
                case _:
                    text = "[Needs case added]"

        if block.get("has_children", False):
            text = f"{text} (Has children)"

        return f"{block_type}: {text}"

    async def get_page_content(self, page_id: str):
        """Retrieve and format all blocks from a page"""
        blocks = await self.retrieve_block_children(page_id)
        content = []
        
        for block in blocks:
            text = self.get_text_from_block(block)
            content.append({
                "id": block["id"],
                "type": block["type"],
                "text": text,
                "has_children": block.get("has_children", False)
            })
        
        return content
