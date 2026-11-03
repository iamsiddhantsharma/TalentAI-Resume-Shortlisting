from motor.motor_asyncio import AsyncIOMotorClient

from app.config.settings import settings


class MongoDB:
    """
    Manages the MongoDB connection for TalentAI.
    """

    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.database = None

    async def connect(self) -> None:
        """
        Connect to MongoDB.
        """

        if self.client is not None:
            return

        self.client = AsyncIOMotorClient(
            settings.MONGODB_URI
        )

        self.database = self.client[
            settings.MONGODB_DATABASE
        ]

        # Verify connection
        await self.client.admin.command(
            "ping"
        )

        print(
            "MongoDB connected successfully."
        )

    async def disconnect(self) -> None:
        """
        Close the MongoDB connection.
        """

        if self.client is not None:
            self.client.close()

            self.client = None
            self.database = None

            print(
                "MongoDB connection closed."
            )

    def get_database(self):
        """
        Return the active MongoDB database.
        """

        if self.database is None:
            raise RuntimeError(
                "MongoDB is not connected."
            )

        return self.database


mongodb = MongoDB()
