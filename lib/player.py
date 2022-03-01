from machine import Pin
from utime import ticks_ms, ticks_diff

from lib.tm1637 import TM1637

DISPLAY_BRIGHTNESS = 2
FLASH_DURATION = 500

class Player():
    def __init__(
        self,
        time: int,
        button_pin: int,
        button_handler: function,
        display_clock: int,
        display_dio: int,
        led_pin: int,
        game_over: function
    ) -> None:
        self.time = time
        self.event_time = None
        
        self.button = Pin(
            button_pin,
            Pin.IN,
            Pin.PULL_DOWN
        )
        self.button.irq(trigger=Pin.IRQ_RISING, handler=button_handler)
        
        self.display = TM1637(clk=Pin(display_clock), dio=Pin(display_dio))
        self.display.brightness(DISPLAY_BRIGHTNESS)
        self.display_time()
        
        self.led = Pin(led_pin, Pin.OUT)
        self.led.value(0)
        
        self.flash_state = True
        
        self.game_over = game_over

    def reset(self, time: int):
        self.time = time
        self.event_time = None
        self.flash_state = True
        self.led.value(0)
        self.display_time()
    
    def activate(self):
        self.event_time = ticks_ms()
        
    def display_time(self):
        if self.time < 0:
            self.time = 0
            
        total_seconds:int = self.time / 1000
        mins = int(total_seconds / 60)
        secs = int(total_seconds % 60)
        
        self.display.numbers(mins, secs)
        
    def flash_display(self, segment: int):
        now = ticks_ms()
        delta_time = ticks_diff(now, self.event_time)
        if delta_time >= FLASH_DURATION:
            self.event_time = now
            if self.flash_state:
                self.flash_state = False
                total_seconds: int = self.time / 1000
                if segment == 0:
                    # hide minutes
                    secs = int(total_seconds % 60)
                    string_secs = str(secs) if secs >= 10 else "0" + str(secs)
                    self.display.show("  " + string_secs)
                else:
                    # hide seconds
                    mins = int(total_seconds / 60)
                    string_mins = str(mins) if mins >= 10 else "0" + str(mins)
                    self.display.show(string_mins + "  ")
            else:
                self.flash_state = True
                self.display_time()
        
    def set_time(self, segment: int, value: int):
        total_seconds: int = self.time / 1000
        if segment == 0:
            # save the seconds
            seconds = int(total_seconds % 60) * 1000
            minutes = value * 60 * 1000
            self.time = minutes + seconds
        elif segment == 1:
            # save the minutes
            value_to_use = value if value < 60 else 59
            minutes = int(total_seconds / 60) * 60 * 1000
            seconds = value_to_use * 1000
            self.time = minutes + seconds
            
    def get_time(self, segment: int) -> int:
        total_seconds: int = self.time / 1000
        return total_seconds / 60 if segment == 0 else total_seconds % 60
        
    def update_time(self):
        now = ticks_ms()
        delta_time = ticks_diff(now, self.event_time)
        self.event_time = now
        self.time = self.time - delta_time
        self.display_time()
        
        if self.time <= 0:
            self.led.value(1)
            self.game_over()