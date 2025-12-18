import pika
import os
import sys


class RabbitMQClient:
    def __init__(self, queue_names=None):
        """
        Initialize RabbitMQ client.

        Args:
            queue_names (list): List of queue names (station names) to subscribe to.
                               If None, will use "tec_data" for backward compatibility.
        """
        # Инициализация RabbitMQ
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "95.215.56.197")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", 5672))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "user")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "123")

        # Подключение к RabbitMQ
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                credentials=pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password)
            )
        )
        self.channel = self.connection.channel()

        # Сохраняем список очередей для подписки
        self.queue_names = queue_names if queue_names else ["tec_data"]

        # Создание очередей с TTL 24 часа (если они еще не созданы)
        for queue_name in self.queue_names:
            self.channel.queue_declare(
                queue=queue_name,
                arguments={"x-message-ttl": 86400000}  # 24 часа в миллисекундах
            )

    def start_consuming(self):
        """
        Начинает получать сообщения из очередей.
        """

        def callback(ch, method, properties, body):
            # Показываем имя очереди и данные
            print(f"[{method.routing_key}] {body.decode()}")

        # Подписываемся на все указанные очереди
        for queue_name in self.queue_names:
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=True
            )

        print(f' [*] Subscribed to queues: {", ".join(self.queue_names)}')
        print(' [*] Waiting for messages. To exit press CTRL+C')
        self.channel.start_consuming()


if __name__ == "__main__":
    # Пример использования:
    # python rabbitmq_client.py BOR1 ALGO       - подписка на несколько станций
    # python rabbitmq_client.py                 - подписка на старую очередь "tec_data"

    if len(sys.argv) > 1:
        # Если переданы аргументы, используем их как имена очередей (станций)
        queues = sys.argv[1:]
        print(f"Subscribing to specific stations: {', '.join(queues)}")
        client = RabbitMQClient(queue_names=queues)
    else:
        # Без аргументов - используем старый режим
        print("No stations specified, using default 'tec_data' queue")
        client = RabbitMQClient()

    client.start_consuming()
