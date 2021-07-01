from unittest import mock, TestCase

from typing import Any, Dict

import lambda_function


def _generate_event(chat_id: str, user_id: str, message: str) -> Dict[str, Any]:
    return {
        'message': {
            'chat': {
                'id': chat_id
            },
            'from': {
                'id': user_id
            },
            'text': message
        }
    }


class Test(TestCase):
    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_unknown_messages(self, mock_send_message, mock_add_history):
        chat_id = 'random_chat_id'

        for unknown_message in ['unknown_message', '-123', '0']:
            with self.subTest(unknown_message=unknown_message):
                event = _generate_event(chat_id=chat_id, user_id='admin', message=unknown_message)

                lambda_function.telegram_bot_main(event)

                mock_send_message.assert_called_with(lambda_function.UNKNOWN_MSG, chat_id)
                mock_add_history.assert_called_with(event)

    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_start_message(self, mock_send_message, mock_add_history):
        chat_id = 'random_chat_id'
        event = _generate_event(chat_id=chat_id, user_id='admin', message='/start')

        lambda_function.telegram_bot_main(event)

        mock_send_message.assert_called_with(lambda_function.INSTRUCTION_MESSAGE, chat_id)
        mock_add_history.assert_called_with(event)

    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_tenge_message(self, mock_send_message, mock_add_history):
        chat_id = 'random_chat_id'
        event = _generate_event(chat_id=chat_id, user_id='admin', message='/tenge')

        lambda_function.telegram_bot_main(event)

        mock_send_message.assert_called_with(lambda_function.AMOUNT_KZT2KRW_MSG, chat_id)
        mock_add_history.assert_called_with(event)

    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_won_message(self, mock_send_message, mock_add_history):
        chat_id = 'random_chat_id'
        event = _generate_event(chat_id=chat_id, user_id='admin', message='/won')

        lambda_function.telegram_bot_main(event)

        mock_send_message.assert_called_with(lambda_function.AMOUNT_KRW2KZT_MSG, chat_id)
        mock_add_history.assert_called_with(event)

    @mock.patch('lambda_function.previous_message')
    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_positive_numeric_message_and_unknown_previous_messages(
            self, mock_send_message, mock_add_history, mock_previous_message):
        chat_id = 'random_chat_id'
        user_id = 'admin'

        for previous_message in ['unknown_message', '-123', '0']:
            with self.subTest():
                event = _generate_event(chat_id=chat_id, user_id=user_id, message='123')

                mock_previous_message.return_value = previous_message
                lambda_function.telegram_bot_main(event)

                mock_previous_message.assert_called_with(user_id)
                mock_send_message.assert_called_with(lambda_function.UNKNOWN_MSG, chat_id)
                mock_add_history.assert_called_with(event)
