from unittest import mock, TestCase

from typing import Any, Dict

import lambda_function


def _generate_event(chat_id: str, user_id: str, text: str) -> Dict[str, Any]:
    return {
        'message': {
            'chat': {
                'id': chat_id
            },
            'from': {
                'id': user_id
            },
            'text': text
        }
    }


class Test(TestCase):
    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_unknown_message(self, mock_send_message, mock_add_history):
        chat_id = 'random_chat_id'
        event = _generate_event(chat_id=chat_id, user_id='admin', text='unknown_message')

        lambda_function.telegram_bot_main(event)

        mock_send_message.assert_called_with(lambda_function.UNKNOWN_MSG, chat_id)
        mock_add_history.assert_called_with(event)

    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_start_message(self, mock_send_message, mock_add_history):
        chat_id = 'random_chat_id'
        event = _generate_event(chat_id=chat_id, user_id='admin', text='/start')

        lambda_function.telegram_bot_main(event)

        mock_send_message.assert_called_with(lambda_function.INSTRUCTION_MESSAGE, chat_id)
        mock_add_history.assert_called_with(event)

    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_tenge_message(self, mock_send_message, mock_add_history):
        chat_id = 'random_chat_id'
        event = _generate_event(chat_id=chat_id, user_id='admin', text='/tenge')

        lambda_function.telegram_bot_main(event)

        mock_send_message.assert_called_with(lambda_function.AMOUNT_KZT2KRW_MSG, chat_id)
        mock_add_history.assert_called_with(event)

    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_won_message(self, mock_send_message, mock_add_history):
        chat_id = 'random_chat_id'
        event = _generate_event(chat_id=chat_id, user_id='admin', text='/won')

        lambda_function.telegram_bot_main(event)

        mock_send_message.assert_called_with(lambda_function.AMOUNT_KRW2KZT_MSG, chat_id)
        mock_add_history.assert_called_with(event)
