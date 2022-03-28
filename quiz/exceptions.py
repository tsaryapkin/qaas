from rest_framework.exceptions import APIException


class QuizException(APIException):
    """
    Base Api exception for quiz application
    """

    status_code = 400
