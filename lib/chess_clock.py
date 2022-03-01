from machine import Pin
from utime import sleep_ms, ticks_ms, ticks_diff

from lib.enums import ClockMode
from lib.player import Player
from lib.rotary_irq_rp2 import RotaryIRQ

# Pins
PLAYER_1_BUTTON: int = 2
PLAYER_2_BUTTON: int = 3
PLAYER_1_DIO: int = 4
PLAYER_1_CLOCK: int = 5
PLAYER_2_DIO: int = 6
PLAYER_2_CLOCK: int = 7
PLAYER_1_LED: int = 8
PLAYER_2_LED: int = 9
BUZZER: int = 10
ROTARY_SW: int = 11
ROTARY_DT: int = 12
ROTARY_CLK: int = 13
RESET_BUTTON: int = 14

# Clock Variables
DEFAULT_START_TIME: int = 600000
DEBOUNCE_DURATION = 200

class ChessClock():
    def __init__(self):
        self.player_1 = Player(
            time=DEFAULT_START_TIME,
            button_pin=PLAYER_1_BUTTON,
            button_handler=self.player_handler,
            display_clock=PLAYER_1_CLOCK,
            display_dio=PLAYER_1_DIO,
            led_pin=PLAYER_1_LED,
            game_over=self.game_over_handler
        )
        self.player_2 = Player(
            time=DEFAULT_START_TIME,
            button_pin=PLAYER_2_BUTTON,
            button_handler=self.player_handler,
            display_clock=PLAYER_2_CLOCK,
            display_dio=PLAYER_2_DIO,
            led_pin=PLAYER_2_LED,
            game_over=self.game_over_handler
        )
        
        self.buzzer = Pin(BUZZER, Pin.OUT)
        self.buzzer.value(0)
        
        self.settings_button = Pin(ROTARY_SW, Pin.IN, Pin.PULL_DOWN)
        self.settings_button.irq(trigger=Pin.IRQ_FALLING, handler=self.settings_handler)
        self.settings_press = ticks_ms()
        
        self.reset_button = Pin(RESET_BUTTON, Pin.IN, Pin.PULL_DOWN)
        self.reset_button.irq(trigger=Pin.IRQ_RISING, handler=self.reset_handler)
        self.reset_press = ticks_ms()
        
        self.encoder = RotaryIRQ(
            pin_num_clk=13,
            pin_num_dt=12,
            min_val=0,
            max_val=60,
            reverse=True,
            range_mode=RotaryIRQ.RANGE_WRAP
        )
        self.encoder.add_listener(self.encoder_handler)
        
        self.active_player:Player = None
        self.edit_player:Player = None
        self.edit_segment:int = 0
        self.winner:bool = False
        self.started:bool = False
        self.mode = ClockMode.PLAY
        
    def reset_clock(self):
        self.active_player = None
        self.edit_player = None
        self.edit_segment = 0
        self.winner = False
        self.started = False
        self.mode = ClockMode.PLAY
        self.player_1.reset(DEFAULT_START_TIME)
        self.player_2.reset(DEFAULT_START_TIME)
        
    def player_handler(self, pin):
        if self.mode == ClockMode.PLAY:
            self.started = True
            if pin is self.player_1.button:
                self.active_player = self.player_2
                self.player_2.activate()
            elif pin is self.player_2.button:
                self.active_player = self.player_1
                self.player_1.activate()
                
    def encoder_handler(self):
        if self.mode == ClockMode.SETUP:
            value = self.encoder.value()
            self.edit_player.set_time(self.edit_segment, value)
    
    def reset_handler(self, pin):
        now = ticks_ms()
        
        if ticks_diff(now, self.reset_press) > DEBOUNCE_DURATION:
            self.reset_press = now
            self.reset_clock()
            
    def settings_handler(self, pin):
        now = ticks_ms()
        
        if ticks_diff(now, self.settings_press) > DEBOUNCE_DURATION:
            self.settings_press = now
            
            if self.mode == ClockMode.PLAY and not self.winner and self.started:
                self.mode = ClockMode.PAUSE
                
            elif self.mode == ClockMode.PLAY and not self.winner and not self.started:
                self.mode = ClockMode.SETUP
                self.edit_player = self.player_1
                segment_time = int(self.edit_player.get_time(self.edit_segment))
                self.encoder.set(value=segment_time)
                self.edit_player.activate()
                
            elif self.mode == ClockMode.PLAY and self.winner:
                self.reset_clock()
                
            elif self.mode == ClockMode.PAUSE:
                self.active_player.activate()
                self.mode = ClockMode.PLAY
                
            elif self.mode == ClockMode.SETUP:
                self.edit_segment += 1
                segment_time = int(self.edit_player.get_time(self.edit_segment))
                self.encoder.set(value=segment_time)
                if self.edit_segment == 2 and self.edit_player == self.player_1:
                    self.edit_player.display_time()
                    self.edit_player = self.player_2
                    self.edit_segment = 0
                    segment_time = int(self.edit_player.get_time(self.edit_segment))
                    self.encoder.set(value=segment_time)
                    self.edit_player.activate()
                elif self.edit_segment == 2 and self.edit_player == self.player_2:
                    self.edit_player.display_time()
                    self.edit_player = None
                    self.edit_segment = 0
                    self.mode = ClockMode.PLAY
            
    def game_over_handler(self):
        self.winner = True
        self.active_player = None
        for i in range(10):
            self.buzzer.toggle()
            sleep_ms(100)
    
    def update_timer(self, player: Player):
        if player != None:
            player.update_time()
        
    def start(self):
        while True:
            if self.mode == ClockMode.PLAY and not self.winner:
                self.update_timer(self.active_player)
            elif self.mode == ClockMode.PAUSE:
                pass
            elif self.mode == ClockMode.SETUP:
                self.edit_player.flash_display(self.edit_segment)
                sleep_ms(100)