"""
Human Simulator - Bezier curves and natural mouse movement.

Implements BE-02: Simulation of human behavior to avoid detection.
- Mouse movement via Bezier curves
- Random scroll patterns
- Natural typing with variable speed
"""

import asyncio
import math
import random
from dataclasses import dataclass
from typing import Optional

from playwright.async_api import Page, ElementHandle


@dataclass
class Point:
    """2D point for mouse coordinates."""
    x: float
    y: float


class HumanSimulator:
    """
    Simulates human-like interactions with the browser.
    
    Key techniques:
    - Bezier curve mouse movements (not straight lines)
    - Random micro-movements and overshoots
    - Variable typing speed with occasional pauses
    - Natural scrolling patterns
    """
    
    # Mouse movement parameters
    MOUSE_STEPS_MIN = 20
    MOUSE_STEPS_MAX = 40
    MOUSE_OVERSHOOT_CHANCE = 0.3
    
    # Typing parameters
    TYPING_DELAY_MIN = 0.05  # 50ms
    TYPING_DELAY_MAX = 0.15  # 150ms
    TYPING_PAUSE_CHANCE = 0.1
    TYPING_PAUSE_MIN = 0.3  # 300ms
    TYPING_PAUSE_MAX = 0.8  # 800ms
    
    # Scroll parameters
    SCROLL_STEP_MIN = 100
    SCROLL_STEP_MAX = 300

    def __init__(self, page: Page) -> None:
        """Initialize with Playwright page."""
        self.page = page
        self._current_mouse: Point = Point(0, 0)

    @staticmethod
    def bezier_point(
        t: float,
        p0: Point,
        p1: Point,
        p2: Point,
        p3: Point,
    ) -> Point:
        """
        Calculate point on cubic Bezier curve.
        
        Args:
            t: Parameter from 0 to 1
            p0: Start point
            p1: Control point 1
            p2: Control point 2
            p3: End point
            
        Returns:
            Point on the curve at parameter t
        """
        u = 1 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t
        
        x = uuu * p0.x + 3 * uu * t * p1.x + 3 * u * tt * p2.x + ttt * p3.x
        y = uuu * p0.y + 3 * uu * t * p1.y + 3 * u * tt * p2.y + ttt * p3.y
        
        return Point(x, y)

    def generate_bezier_path(
        self,
        start: Point,
        end: Point,
        steps: Optional[int] = None,
    ) -> list[Point]:
        """
        Generate natural mouse path using Bezier curves.
        
        Args:
            start: Starting position
            end: Target position
            steps: Number of points (random if None)
            
        Returns:
            List of points forming the path
        """
        if steps is None:
            steps = random.randint(self.MOUSE_STEPS_MIN, self.MOUSE_STEPS_MAX)
        
        # Generate control points for natural curve
        dist = math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)
        spread = dist * 0.3  # Control point spread
        
        # Randomize control points
        cp1 = Point(
            start.x + (end.x - start.x) * 0.3 + random.uniform(-spread, spread),
            start.y + (end.y - start.y) * 0.3 + random.uniform(-spread, spread),
        )
        cp2 = Point(
            start.x + (end.x - start.x) * 0.7 + random.uniform(-spread, spread),
            start.y + (end.y - start.y) * 0.7 + random.uniform(-spread, spread),
        )
        
        # Generate path points
        path = []
        for i in range(steps + 1):
            t = i / steps
            # Add easing (slow start and end)
            t = t * t * (3 - 2 * t)
            point = self.bezier_point(t, start, cp1, cp2, end)
            # Add micro-jitter
            point.x += random.uniform(-1, 1)
            point.y += random.uniform(-1, 1)
            path.append(point)
            
        return path

    async def move_mouse_to(
        self,
        x: float,
        y: float,
        overshoot: bool = True,
    ) -> None:
        """
        Move mouse to target using natural Bezier curve.
        
        Args:
            x: Target X coordinate
            y: Target Y coordinate
            overshoot: Whether to overshoot and correct
        """
        target = Point(x, y)
        
        # Sometimes overshoot the target
        if overshoot and random.random() < self.MOUSE_OVERSHOOT_CHANCE:
            offset = random.uniform(5, 15)
            angle = random.uniform(0, 2 * math.pi)
            overshoot_point = Point(
                x + math.cos(angle) * offset,
                y + math.sin(angle) * offset,
            )
            
            # Move to overshoot point
            path = self.generate_bezier_path(self._current_mouse, overshoot_point)
            for point in path:
                await self.page.mouse.move(point.x, point.y)
                await asyncio.sleep(random.uniform(0.001, 0.005))
            
            self._current_mouse = overshoot_point
            await asyncio.sleep(random.uniform(0.05, 0.1))
        
        # Move to actual target
        path = self.generate_bezier_path(self._current_mouse, target)
        for point in path:
            await self.page.mouse.move(point.x, point.y)
            await asyncio.sleep(random.uniform(0.001, 0.005))
        
        self._current_mouse = target

    async def click_element(
        self,
        element: ElementHandle,
        offset_variance: int = 5,
    ) -> None:
        """
        Click element with natural mouse movement.
        
        Args:
            element: Element to click
            offset_variance: Random offset from center
        """
        box = await element.bounding_box()
        if not box:
            await element.click()
            return
        
        # Calculate target with offset
        x = box["x"] + box["width"] / 2 + random.uniform(-offset_variance, offset_variance)
        y = box["y"] + box["height"] / 2 + random.uniform(-offset_variance, offset_variance)
        
        await self.move_mouse_to(x, y)
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await self.page.mouse.click(x, y)

    async def type_text(
        self,
        text: str,
        element: Optional[ElementHandle] = None,
    ) -> None:
        """
        Type text with human-like delays.
        
        Args:
            text: Text to type
            element: Optional element to click first
        """
        if element:
            await self.click_element(element)
            await asyncio.sleep(random.uniform(0.1, 0.2))
        
        for char in text:
            # Variable typing speed
            delay = random.uniform(self.TYPING_DELAY_MIN, self.TYPING_DELAY_MAX)
            
            # Occasional pause (thinking)
            if random.random() < self.TYPING_PAUSE_CHANCE:
                await asyncio.sleep(
                    random.uniform(self.TYPING_PAUSE_MIN, self.TYPING_PAUSE_MAX)
                )
            
            await self.page.keyboard.type(char, delay=delay * 1000)

    async def scroll_page(
        self,
        direction: str = "down",
        amount: Optional[int] = None,
    ) -> None:
        """
        Scroll page with natural pattern.
        
        Args:
            direction: 'up' or 'down'
            amount: Scroll amount (random if None)
        """
        if amount is None:
            amount = random.randint(self.SCROLL_STEP_MIN, self.SCROLL_STEP_MAX)
        
        if direction == "up":
            amount = -amount
        
        # Scroll in small increments
        steps = random.randint(3, 6)
        step_amount = amount // steps
        
        for _ in range(steps):
            await self.page.mouse.wheel(0, step_amount)
            await asyncio.sleep(random.uniform(0.05, 0.15))

    async def random_scroll(self) -> None:
        """Perform random scrolling to simulate reading."""
        scroll_count = random.randint(2, 5)
        
        for _ in range(scroll_count):
            direction = random.choice(["down", "down", "down", "up"])  # Bias toward down
            await self.scroll_page(direction)
            await asyncio.sleep(random.uniform(0.5, 2.0))

    async def hover_element(self, element: ElementHandle) -> None:
        """Hover over element with natural movement."""
        box = await element.bounding_box()
        if box:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            await self.move_mouse_to(x, y, overshoot=False)

    async def wait_human(self, min_sec: float = 0.5, max_sec: float = 2.0) -> None:
        """Wait a random human-like duration."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))
