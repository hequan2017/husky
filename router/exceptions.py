# -*- encoding: utf-8 -*-
"""
users 的自定义 exceptions
"""


class CaptchaError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)