"""
Tactical Map Manager - Grid-based combat maps with token positions
"""

import os
import json
from typing import Optional, List, Dict, Any, Tuple
from threading import Lock
from dataclasses import dataclass, asdict

MAPS_DIR = os.path.join(os.path.dirname(__file__), '..', 'maps')
os.makedirs(MAPS_DIR, exist_ok=True)

_map_locks = {}


# ============ DATA CLASSES ============

@dataclass
class Token:
    """A token on the map (player, monster, or object)."""
    name: str
    x: int
    y: int
    token_type: str = "player"  # player, enemy, npc, object
    symbol: str = "●"
    color: str = "blue"
    size: int = 1  # 1 = medium, 2 = large, 3 = huge, 4 = gargantuan
    notes: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Token':
        return cls(**data)


@dataclass
class MapCell:
    """A single cell on the map."""
    terrain: str = "floor"  # floor, wall, water, difficult, pit, door, etc.
    symbol: str = "."
    passable: bool = True
    cover: str = ""  # half, three-quarters, full
    notes: str = ""


# ============ TERRAIN TYPES ============

TERRAIN_TYPES = {
    "floor": {"symbol": ".", "passable": True, "name": "Floor"},
    "wall": {"symbol": "#", "passable": False, "name": "Wall"},
    "water": {"symbol": "~", "passable": True, "difficult": True, "name": "Water"},
    "difficult": {"symbol": ":", "passable": True, "difficult": True, "name": "Difficult Terrain"},
    "pit": {"symbol": "O", "passable": True, "hazard": True, "name": "Pit"},
    "door": {"symbol": "+", "passable": True, "name": "Door"},
    "door_locked": {"symbol": "X", "passable": False, "name": "Locked Door"},
    "stairs_up": {"symbol": "<", "passable": True, "name": "Stairs Up"},
    "stairs_down": {"symbol": ">", "passable": True, "name": "Stairs Down"},
    "rubble": {"symbol": "^", "passable": True, "difficult": True, "cover": "half", "name": "Rubble"},
    "pillar": {"symbol": "O", "passable": False, "cover": "half", "name": "Pillar"},
    "tree": {"symbol": "T", "passable": False, "cover": "half", "name": "Tree"},
    "bush": {"symbol": "*", "passable": True, "difficult": True, "cover": "half", "name": "Bush"},
    "lava": {"symbol": "L", "passable": True, "hazard": True, "name": "Lava"},
    "ice": {"symbol": "=", "passable": True, "difficult": True, "name": "Ice"},
}

TOKEN_SYMBOLS = {
    "player": {"symbol": "●", "color": "🔵"},
    "enemy": {"symbol": "◆", "color": "🔴"},
    "npc": {"symbol": "○", "color": "🟢"},
    "object": {"symbol": "□", "color": "⬜"},
    "boss": {"symbol": "★", "color": "🟣"},
}

SIZE_NAMES = {
    1: "Medium",
    2: "Large",
    3: "Huge",
    4: "Gargantuan",
}


# ============ MAP CLASS ============

class TacticalMap:
    """A tactical battle map with grid and tokens."""
    
    def __init__(self, width: int = 20, height: int = 15, name: str = "Battle Map"):
        self.name = name
        self.width = width
        self.height = height
        self.grid: List[List[str]] = [["." for _ in range(width)] for _ in range(height)]
        self.tokens: Dict[str, Token] = {}  # name -> Token
        self.notes: str = ""
        self.scale: int = 5  # 5 feet per square
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "grid": self.grid,
            "tokens": {name: t.to_dict() for name, t in self.tokens.items()},
            "notes": self.notes,
            "scale": self.scale,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TacticalMap':
        map_obj = cls(
            width=data.get("width", 20),
            height=data.get("height", 15),
            name=data.get("name", "Battle Map")
        )
        map_obj.grid = data.get("grid", map_obj.grid)
        map_obj.tokens = {
            name: Token.from_dict(t) for name, t in data.get("tokens", {}).items()
        }
        map_obj.notes = data.get("notes", "")
        map_obj.scale = data.get("scale", 5)
        return map_obj
    
    def set_terrain(self, x: int, y: int, terrain: str) -> bool:
        """Set terrain at a position."""
        if not self._in_bounds(x, y):
            return False
        
        terrain_data = TERRAIN_TYPES.get(terrain, TERRAIN_TYPES["floor"])
        self.grid[y][x] = terrain_data["symbol"]
        return True
    
    def add_token(self, name: str, x: int, y: int, token_type: str = "player", size: int = 1) -> Optional[Token]:
        """Add a token to the map."""
        if not self._in_bounds(x, y):
            return None
        
        symbol_data = TOKEN_SYMBOLS.get(token_type, TOKEN_SYMBOLS["player"])
        token = Token(
            name=name,
            x=x,
            y=y,
            token_type=token_type,
            symbol=symbol_data["symbol"],
            size=size
        )
        self.tokens[name.lower()] = token
        return token
    
    def remove_token(self, name: str) -> bool:
        """Remove a token from the map."""
        name_lower = name.lower()
        if name_lower in self.tokens:
            del self.tokens[name_lower]
            return True
        return False
    
    def move_token(self, name: str, x: int, y: int) -> Optional[Tuple[int, int]]:
        """Move a token to a new position. Returns old position or None."""
        name_lower = name.lower()
        if name_lower not in self.tokens:
            return None
        
        if not self._in_bounds(x, y):
            return None
        
        token = self.tokens[name_lower]
        old_pos = (token.x, token.y)
        token.x = x
        token.y = y
        return old_pos
    
    def get_token(self, name: str) -> Optional[Token]:
        """Get a token by name."""
        return self.tokens.get(name.lower())
    
    def get_token_at(self, x: int, y: int) -> Optional[Token]:
        """Get the token at a position."""
        for token in self.tokens.values():
            if token.x == x and token.y == y:
                return token
        return None
    
    def get_distance(self, name1: str, name2: str) -> Optional[int]:
        """Get distance in feet between two tokens (D&D diagonal = 5ft)."""
        t1 = self.get_token(name1)
        t2 = self.get_token(name2)
        
        if not t1 or not t2:
            return None
        
        # D&D uses "every second diagonal costs 10ft" but simplified here
        dx = abs(t1.x - t2.x)
        dy = abs(t1.y - t2.y)
        
        # Use diagonal distance (Chebyshev distance for simplicity)
        squares = max(dx, dy)
        return squares * self.scale
    
    def get_tokens_in_range(self, name: str, range_feet: int) -> List[Token]:
        """Get all tokens within range of a token."""
        center = self.get_token(name)
        if not center:
            return []
        
        range_squares = range_feet // self.scale
        in_range = []
        
        for token in self.tokens.values():
            if token.name.lower() == name.lower():
                continue
            
            dx = abs(token.x - center.x)
            dy = abs(token.y - center.y)
            distance = max(dx, dy)
            
            if distance <= range_squares:
                in_range.append(token)
        
        return in_range
    
    def render(self, show_coordinates: bool = True) -> str:
        """Render the map as ASCII art."""
        lines = []
        
        # Header with column numbers
        if show_coordinates:
            header = "   "
            for x in range(self.width):
                header += str(x % 10)
            lines.append(header)
            lines.append("  +" + "-" * self.width + "+")
        else:
            lines.append("+" + "-" * self.width + "+")
        
        # Build token position lookup
        token_positions = {}
        for token in self.tokens.values():
            token_positions[(token.x, token.y)] = token
        
        # Render each row
        for y in range(self.height):
            if show_coordinates:
                row = f"{y:2d}|"
            else:
                row = "|"
            
            for x in range(self.width):
                if (x, y) in token_positions:
                    token = token_positions[(x, y)]
                    # Use first letter of name or symbol
                    row += token.name[0].upper()
                else:
                    row += self.grid[y][x]
            
            row += "|"
            lines.append(row)
        
        # Footer
        if show_coordinates:
            lines.append("  +" + "-" * self.width + "+")
        else:
            lines.append("+" + "-" * self.width + "+")
        
        return "\n".join(lines)
    
    def render_discord(self) -> str:
        """Render map with Discord-friendly formatting."""
        output = f"**🗺️ {self.name}** ({self.width}x{self.height}, {self.scale}ft/square)\n"
        output += "```\n"
        output += self.render(show_coordinates=True)
        output += "\n```\n"
        
        # Token legend
        if self.tokens:
            output += "**Tokens:**\n"
            for token in self.tokens.values():
                emoji = TOKEN_SYMBOLS.get(token.type, TOKEN_SYMBOLS["player"])["color"]
                size_str = f" ({SIZE_NAMES.get(token.size, 'Medium')})" if token.size > 1 else ""
                output += f"{emoji} **{token.name[0].upper()}** = {token.name} at ({token.x},{token.y}){size_str}\n"
        
        return output
    
    def _in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are within map bounds."""
        return 0 <= x < self.width and 0 <= y < self.height


# ============ MAP STORAGE ============

def _get_map_path(channel_id: str) -> str:
    return os.path.join(MAPS_DIR, f'{channel_id}.json')


def load_map(channel_id: str) -> Optional[TacticalMap]:
    """Load the tactical map for a channel."""
    path = _get_map_path(channel_id)
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return TacticalMap.from_dict(data)
    except:
        return None


def save_map(channel_id: str, map_obj: TacticalMap):
    """Save the tactical map for a channel."""
    path = _get_map_path(channel_id)
    lock = _map_locks.setdefault(channel_id, Lock())
    
    with lock:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(map_obj.to_dict(), f, indent=2)


def delete_map(channel_id: str) -> bool:
    """Delete the map for a channel."""
    path = _get_map_path(channel_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


# ============ MAP TEMPLATES ============

def create_dungeon_room(width: int = 15, height: int = 10, name: str = "Dungeon Room") -> TacticalMap:
    """Create a simple dungeon room with walls."""
    map_obj = TacticalMap(width, height, name)
    
    # Walls around the edges
    for x in range(width):
        map_obj.grid[0][x] = "#"
        map_obj.grid[height-1][x] = "#"
    
    for y in range(height):
        map_obj.grid[y][0] = "#"
        map_obj.grid[y][width-1] = "#"
    
    # Door in the middle of the south wall
    map_obj.grid[height-1][width//2] = "+"
    
    return map_obj


def create_forest_clearing(width: int = 20, height: int = 15, name: str = "Forest Clearing") -> TacticalMap:
    """Create a forest clearing with trees around the edges."""
    map_obj = TacticalMap(width, height, name)
    
    # Scatter trees around the edges
    import random
    for x in range(width):
        if random.random() < 0.3:
            map_obj.grid[0][x] = "T"
        if random.random() < 0.3:
            map_obj.grid[height-1][x] = "T"
    
    for y in range(1, height-1):
        if random.random() < 0.3:
            map_obj.grid[y][0] = "T"
        if random.random() < 0.3:
            map_obj.grid[y][width-1] = "T"
    
    # A few bushes scattered around
    for _ in range(5):
        x = random.randint(3, width-4)
        y = random.randint(3, height-4)
        map_obj.grid[y][x] = "*"
    
    return map_obj


def create_tavern(width: int = 20, height: int = 15, name: str = "Tavern") -> TacticalMap:
    """Create a tavern interior."""
    map_obj = TacticalMap(width, height, name)
    
    # Walls
    for x in range(width):
        map_obj.grid[0][x] = "#"
        map_obj.grid[height-1][x] = "#"
    for y in range(height):
        map_obj.grid[y][0] = "#"
        map_obj.grid[y][width-1] = "#"
    
    # Door at bottom
    map_obj.grid[height-1][width//2] = "+"
    
    # Bar counter (represented as pillars)
    bar_y = 3
    for x in range(3, 10):
        map_obj.grid[bar_y][x] = "O"
    
    # Some tables (pillars)
    tables = [(5, 8), (10, 8), (15, 8), (5, 11), (10, 11), (15, 11)]
    for tx, ty in tables:
        if 0 < tx < width-1 and 0 < ty < height-1:
            map_obj.grid[ty][tx] = "O"
    
    # Stairs up in corner
    map_obj.grid[1][width-2] = "<"
    
    return map_obj


def create_cave(width: int = 25, height: int = 18, name: str = "Cave") -> TacticalMap:
    """Create an irregular cave."""
    map_obj = TacticalMap(width, height, name)
    
    # Fill with walls
    for y in range(height):
        for x in range(width):
            map_obj.grid[y][x] = "#"
    
    # Carve out irregular cave shape
    import random
    center_x, center_y = width // 2, height // 2
    
    # Main chamber
    for y in range(3, height-3):
        for x in range(3, width-3):
            dx = abs(x - center_x)
            dy = abs(y - center_y)
            # Irregular ellipse
            if (dx / (width/3))**2 + (dy / (height/3))**2 < 1 + random.random() * 0.3:
                map_obj.grid[y][x] = "."
    
    # Entrance tunnel
    for y in range(height-3, height):
        map_obj.grid[y][center_x] = "."
    
    # Some rubble
    for _ in range(8):
        x = random.randint(4, width-5)
        y = random.randint(4, height-5)
        if map_obj.grid[y][x] == ".":
            map_obj.grid[y][x] = "^"
    
    # A pit
    pit_x = random.randint(5, width-6)
    pit_y = random.randint(5, height-6)
    if map_obj.grid[pit_y][pit_x] == ".":
        map_obj.grid[pit_y][pit_x] = "O"
    
    return map_obj


MAP_TEMPLATES = {
    "dungeon": create_dungeon_room,
    "forest": create_forest_clearing,
    "tavern": create_tavern,
    "cave": create_cave,
}


def create_from_template(template: str, **kwargs) -> Optional[TacticalMap]:
    """Create a map from a template name."""
    if template in MAP_TEMPLATES:
        return MAP_TEMPLATES[template](**kwargs)
    return None
