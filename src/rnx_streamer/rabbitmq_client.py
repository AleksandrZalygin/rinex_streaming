import pika
import os


class RabbitMQClient:
    def __init__(self):
        # Инициализация RabbitMQ
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", 5672))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")

        # Подключение к RabbitMQ
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                credentials=pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password)
            )
        )
        self.channel = self.connection.channel()

        # Создание очереди с TTL 24 часа (если она еще не создана)
        self.queue_name = "tec_data"
        self.channel.queue_declare(
            queue=self.queue_name,
            arguments={"x-message-ttl": 86400000}  # 24 часа в миллисекундах
        )

    def start_consuming(self):
        """
        Начинает получать сообщения из очереди.
        """

        def callback(ch, method, properties, body):
            print(f" {body.decode()}")

        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=callback,
            auto_ack=True
        )

        print(' [*] Waiting for messages. To exit press CTRL+C')
        self.channel.start_consuming()


if __name__ == "__main__":
    client = RabbitMQClient()
    client.start_consuming()
