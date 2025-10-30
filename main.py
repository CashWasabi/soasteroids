from typing import Optional
import time
from enum import Enum
import pyray as rl
import random
import tools
# import numpy as np

INIT_WIDTH = 800
INIT_HEIGHT = 600


# ===========
# DATA TYPES
# ===========
class EntityId:
    def __init__(self, index: int = 0, generation: int = 0):
        self.index = index
        self.generation = generation


class EntityType(Enum):
    NONE = 0
    PLAYER = 1
    ENEMY = 2
    PROJECTILE = 3


class ContextType(Enum):
    PERSISTENT = 0
    WORLD = 1
    SCENE = 2


class RigidbodyType(Enum):
    NONE = 0
    STATIC = 1
    KINEMATIC = 1
    DYNAMIC = 2


# TODO: LAYERS AND MASKS COULD BE ENUMS


class Layer(Enum):
    DEFAULT = b"0x44"
    ENEMY = b"0x00"
    PLAYER = b"0x00"
    ENEMY_PROJECTILE = b"0x00"
    PLAYER_PROJECTILE = b"0x00"


class Mask(Enum):
    DEFAULT = b"0x44"
    ENEMY = b"0x00"
    PLAYER = b"0x00"
    ENEMY_PROJECTILE = b"0x00"
    PLAYER_PROJECTILE = b"0x00"


# ============
# ENTITY DATA
# ============
class EntitySlotMap:
    def __init__(self, count):
        assert count > 0
        self._free_list: set[EntityId] = set()

        self.active: list[bool] = []
        self.default_active: bool = False

        self.type: list[EntityType] = []
        self.default_type: EntityType = EntityType.NONE

        self.context_type: list[ContextType] = []
        self.default_context_type: ContextType = ContextType.PERSISTENT

        self.rb_type: list[RigidbodyType] = []
        self.default_rb_type: RigidbodyType = RigidbodyType.NONE

        self.color: list[rl.Color] = []
        self.default_color: rl.Color = rl.RAYWHITE

        self.px: list[float] = []
        self.default_px: float = 0

        self.py: list[float] = []
        self.default_py: float = 0

        self.look_dir_x: list[float] = []
        self.default_look_dir_x: float = 0

        self.look_dir_y: list[float] = []
        self.default_look_dir_y: float = 0

        self.vx: list[float] = []
        self.default_vx: float = 0

        self.vy: list[float] = []
        self.default_vy: float = 0

        self.speed: list[int] = []
        self.default_speed: float = 0

        self.collider_radius: list[float] = []
        self.default_collider_radius: float = 0

        self.collision_layer: list[Layer] = []
        self.default_collision_layer: Layer = Layer.DEFAULT

        self.collision_mask: list[Mask] = []
        self.default_collision_mask: Mask = Mask.DEFAULT

        self.perception: list[float] = []
        self.default_perception: float = 0

        self.weapon_radius: list[float] = []
        self.default_weapon_radius: float = 0

        self.weapon_fire_rate: list[float] = []
        self.default_weapon_fire_rate: float = 0

        self.weapon_last_shot: list[float] = []
        self.default_weapon_last_shot: float = 0

        self.weapon_damage: list[int] = []
        self.default_weapon_damage: float = 0

        self.health: list[int] = []
        self.default_health: float = 0

        self.health_max: list[int] = []  # -1 means invincible?
        self.default_health_max: float = 0

        self.spawn_time: list[float] = []
        self.default_spawn_time: float = 0

        self.life_time: list[float] = []  # -1 means no lifetime?
        self.default_life_time: float = 0

        # set slots
        for i in range(count):
            self._free_list.add(EntityId(i))

            for field_name in [
                i
                for i in dir(self)
                if not i.startswith("_") and not i.startswith("default")
            ]:
                field = getattr(self, field_name)
                if not isinstance(field, list):
                    continue
                field.append(getattr(self, f"default_{field_name}"))

    def is_active(self, entity: EntityId) -> bool:
        return self.active[entity.index]

    def destroy(self, entity: EntityId):
        if not self.active[entity.index]:
            return
        self.active[entity.index] = False

    def create(self) -> EntityId:
        entity = self._free_list.pop()

        for field_name in [
            i
            for i in dir(self)
            if not i.startswith("_") and not i.startswith("default")
        ]:
            field = getattr(self, field_name)
            if not isinstance(field, list):
                continue
            field.append(getattr(self, f"default_{field_name}"))

        self.active[entity.index] = True

        return entity


# ===========
# WORLD DATA
# ===========
class InputState(Enum):
    RELEASED = 0
    JUST_RELEASED = 1
    JUST_PRESSED = 2
    PRESSED = 3


class InputKey:
    def __init__(self, key: rl.KeyboardKey):
        self.key = key
        self.state = InputState.RELEASED

    def update(self):
        match self.state:
            case InputState.RELEASED:
                if rl.is_key_pressed(self.key):
                    self.state = InputState.JUST_PRESSED
            case InputState.JUST_PRESSED:
                if rl.is_key_down(self.key):
                    self.state = InputState.PRESSED
                else:
                    self.state = InputState.JUST_RELEASED
            case InputState.PRESSED:
                if not rl.is_key_down(self.key):
                    self.state = InputState.JUST_RELEASED
            case InputState.JUST_RELEASED:
                if not rl.is_key_pressed(self.key):
                    self.state = InputState.RELEASED


class Inputs:
    def __init__(self):
        self.horizontal = 0
        self.vertical = 0

        self.up_key = InputKey(rl.KeyboardKey.KEY_W)
        self.down_key = InputKey(rl.KeyboardKey.KEY_S)
        self.left_key = InputKey(rl.KeyboardKey.KEY_A)
        self.right_key = InputKey(rl.KeyboardKey.KEY_D)
        self.action_key = InputKey(rl.KeyboardKey.KEY_SPACE)

    def update(self):
        inputs = [
            self.up_key,
            self.down_key,
            self.left_key,
            self.right_key,
            self.action_key,
        ]
        for inp in inputs:
            inp.update()

        self.horizontal = 0
        self.vertical = 0
        if self.up_key.state == InputState.PRESSED:
            self.vertical -= 1
        if self.down_key.state == InputState.PRESSED:
            self.vertical += 1
        if self.left_key.state == InputState.PRESSED:
            self.horizontal -= 1
        if self.right_key.state == InputState.PRESSED:
            self.horizontal += 1


class World:
    def __init__(self, target_fps: int, max_entities: int):
        self.target_fps: float = target_fps
        self.last_time: float = 0
        self.time: float = time.time()
        self.actual_fps: float = 0
        self.dt: float = 0
        self.inputs: Inputs = Inputs()
        self.entities: set[EntityId] = set()  # all active entities
        self.bhv_player: set[EntityId] = set()
        self.bhv_projectile: set[EntityId] = set()
        self.bhv_enemy: set[EntityId] = set()
        self.remove_list: set[EntityId] = set()
        self.slots = EntitySlotMap(max_entities)
        self.physics_system = PhysicsSystem(50, 50)

    def update(self):
        self.actual_fps = rl.get_fps()

        current_time = time.time()
        self.dt = current_time - self.last_time
        self.last_time = self.time
        self.time = current_time

        self.inputs.update()
        self.physics_system.update(self.slots, self.entities)
        self._destroy_entities()

    def push_destroy_entity(self, entity: EntityId):
        self.remove_list.add(entity)

    def _destroy_entities(self):
        for entity in self.remove_list:
            index = entity.index
            match self.slots.type[index]:
                case EntityType.PLAYER:
                    self.bhv_player.remove(entity)
                case EntityType.PROJECTILE:
                    self.bhv_player.remove(entity)
                case EntityType.ENEMY:
                    self.bhv_player.remove(entity)

            self.entities.remove(entity)

            self.slots.destroy(entity)

        self.remove_list.clear()

    def create_entity(self) -> EntityId:
        entity = self.slots.create()
        # TODO: should we move this into slots? It could be an array like px or py
        entity.generation += 1
        self.entities.add(entity)
        return entity

    def create_player(self, px: float, py: float) -> EntityId:
        entity_id = self.create_entity()
        index = entity_id.index

        self.slots.spawn_time[index] = self.time
        self.slots.life_time[index] = -1

        self.slots.type[index] = EntityType.PLAYER
        self.slots.context_type[index] = ContextType.PERSISTENT

        self.slots.collision_layer[index] = Layer.PLAYER
        self.slots.collision_mask[index] = Mask.PLAYER
        self.slots.collider_radius[index] = 10

        self.slots.px[index] = px
        self.slots.py[index] = py
        self.slots.speed[index] = 100

        self.slots.color[index] = rl.BLUE

        self.slots.perception[index] = 100.0

        self.slots.weapon_radius[index] = 100
        self.slots.weapon_fire_rate[index] = 0.5

        self.slots.health_max[index] = 100
        self.slots.health[index] = self.slots.health_max[index]

        self.bhv_player.add(entity_id)

        return entity_id

    def create_projectile(
        self,
        px: float,
        py: float,
        target_dir_x: float,
        target_dir_y: float,
        layer: Layer,
        mask: Mask,
        lifetime: float,
        color: rl.Color,
    ) -> EntityId:
        entity_id = self.create_entity()
        index = entity_id.index

        self.slots.px[index] = px
        self.slots.py[index] = py
        self.slots.look_dir_x[index] = target_dir_x
        self.slots.look_dir_y[index] = target_dir_y
        self.slots.color[index] = color
        self.slots.collision_layer[index] = layer
        self.slots.collision_mask[index] = mask
        self.slots.spawn_time[index] = self.time
        self.slots.life_time[index] = lifetime

        self.slots.type[index] = EntityType.PROJECTILE
        self.slots.context_type[index] = ContextType.PERSISTENT

        self.slots.collider_radius[index] = 2

        self.slots.speed[index] = 100

        self.slots.perception[index] = 0

        self.slots.weapon_radius[index] = 100
        self.slots.weapon_fire_rate[index] = 0.5

        self.slots.health_max[index] = -1
        self.slots.health[index] = self.slots.health_max[index]

        self.bhv_projectile.add(entity_id)

        return entity_id

    def create_enemy(self, px: float, py: float) -> EntityId:
        entity_id = self.create_entity()
        index = entity_id.index

        width = rl.get_screen_width()
        height = rl.get_screen_height()

        look_dir = rl.Vector2(
            random.randrange(-width, width), random.randrange(-height, height)
        )
        look_dir = tools.normalize(look_dir)

        self.slots.px[index] = px
        self.slots.py[index] = py
        self.slots.look_dir_x[index] = look_dir.x
        self.slots.look_dir_y[index] = look_dir.y
        self.slots.color[index] = rl.RED
        self.slots.collision_layer[index] = Layer.ENEMY
        self.slots.collision_mask[index] = Mask.ENEMY
        self.slots.spawn_time[index] = self.time
        self.slots.life_time[index] = -1

        self.slots.type[index] = EntityType.ENEMY
        self.slots.context_type[index] = ContextType.PERSISTENT

        self.slots.collider_radius[index] = 5

        self.slots.speed[index] = 10

        self.slots.perception[index] = 200

        self.slots.weapon_radius[index] = 100
        self.slots.weapon_fire_rate[index] = 0.5

        self.slots.health_max[index] = -1
        self.slots.health[index] = self.slots.health_max[index]

        self.bhv_enemy.add(entity_id)

        return entity_id


class PhysicsSystem:
    def __init__(self, cell_size_x: float, cell_size_y: float):
        self.cell_size_x = cell_size_x
        self.cell_size_y = cell_size_y

        self.cells: dict[rl.Vector2, list[EntityId]] = {}
        self.contacts: list[set[EntityId]] = []

    def update(self, slots: EntitySlotMap, entities: set[EntityId]):
        # CLEAR CELLS AND CONTACTS
        self.cells.clear()
        self.contacts.clear()

        for entity in entities:
            index = entity.index
            self.insertToCells(
                entity,
                slots.px[index],
                slots.py[index],
                slots.collider_radius[index],
            )

        # NARROW PHASE
        # TODO: filter by layers and masks
        i = len(self.contacts)
        while i > 0:
            i -= 1
            a, b = self.contacts[i]
            if not tools.collides(a, b):
                _ = self.contacts.pop()

    def getCell(self, x: int, y: int) -> Optional[list[EntityId]]:
        # to key = (y << 16) | x
        # from key
        # x = key & 0xFFFF      # lower 16 bits
        # y = key >> 16         # upper 16 bits
        self.cells.get((y << 16) | x)

    def insertToCells(self, entity: EntityId, px: float, py: float, radius: float):
        rect = rl.Rectangle(
            px - radius,
            py - radius,
            radius * 2,
            radius * 2,
        )
        area = self.getCollidingCellArea(rect)

        # to key = (y << 16) | x
        # from key
        # x = key & 0xFFFF      # lower 16 bits
        # y = key >> 16         # upper 16 bits
        for x in range(int(area.width)):
            for y in range(int(area.height)):
                key = (y << 16) | x
                if self.cells.get(key) is None:
                    self.cells[key] = []
                else:
                    self.cells[key].append(entity)

    def getCollidingCellArea(self, rect: rl.Rectangle) -> rl.Rectangle:
        top_left = rl.Vector2(rect.x, rect.y)
        bottom_left = rl.Vector2(rect.x + rect.width, rect.y + rect.height)

        top_left_cell = rl.Vector2(
            top_left.x // self.cell_size_x,
            top_left.y // self.cell_size_y,
        )
        bottom_right_cell = rl.Vector2(
            bottom_left.x // self.cell_size_x, bottom_left.y // self.cell_size_y
        )

        return rl.Rectangle(
            top_left_cell.x,
            top_left_cell.y,
            bottom_right_cell.x - top_left_cell.x,
            bottom_right_cell.y - top_left_cell.y,
        )


# =====
# DRAW
# =====
def update_movement(slots: EntitySlotMap, entities: set[EntityId], dt: float):
    width = rl.get_screen_width()
    height = rl.get_screen_height()

    for entity in entities:
        index = entity.index

        vx = slots.vx[index]
        vy = slots.vy[index]

        new_px = slots.px[index] + vx * dt
        new_py = slots.py[index] + vy * dt

        if new_px < 0:
            new_px = width
        if new_px > width:
            new_px = 0
        if new_py < 0:
            new_py = height
        if new_py > height:
            new_py = 0

        # update position
        slots.px[index] = new_px
        slots.py[index] = new_py


# NOTE: entities are weapons
def update_weapon(world: World, slots: EntitySlotMap, entities: set[EntityId]):
    for entity in entities:
        index = entity.index
        if slots.type[index] != EntityType.PROJECTILE:
            continue

        fire_rate = slots.weapon_fire_rate[index]
        last_shot = slots.weapon_last_shot[index]
        if world.time - last_shot < fire_rate:
            continue

        # TODO: check for nearest enemy
        pass


def update_bhv_player(world: World, slots: EntitySlotMap, players: set[EntityId]):
    for player in players:
        index = player.index

        speed = slots.speed[index]
        slots.vx[index] = world.inputs.horizontal * speed
        slots.vy[index] = world.inputs.vertical * speed


def update_bhv_projectile(
    world: World, slots: EntitySlotMap, projectiles: set[EntityId]
):
    for projectile in projectiles:
        index = projectile.index

        life_time = slots.life_time[index]
        spawn_time = slots.spawn_time[index]
        # get world time and check for delta time
        if world.time - spawn_time > life_time:
            world.push_destroy_entity(projectile)


def update_bhv_enemy(
    physics_system: PhysicsSystem,
    slots: EntitySlotMap,
    enemies: set[EntityId],
    dt: float,
):
    _ = physics_system
    for enemy in enemies:
        index = enemy.index
        look_dir_x = slots.look_dir_x[index]
        look_dir_y = slots.look_dir_y[index]
        speed = slots.speed[index]
        slots.vx[index] = look_dir_x * speed * dt
        slots.vy[index] = look_dir_y * speed * dt


# =====
# DRAW
# =====
def draw_player(slots: EntitySlotMap, players: set[EntityId]):
    for player in players:
        index = player.index

        px = slots.px[index]
        py = slots.py[index]
        radius = slots.collider_radius[index]
        color = slots.color[index]

        rl.draw_rectangle(
            int(px - radius),
            int(py - radius),
            radius * 2,
            radius * 2,
            color,
        )


def draw_enemy(slots: EntitySlotMap, enemies: set[EntityId]):
    for enemy in enemies:
        index = enemy.index

        px = slots.px[index]
        py = slots.py[index]
        radius = slots.collider_radius[index]
        color = slots.color[index]

        rl.draw_circle(int(px), int(py), radius, color)


def draw_projectile(slots: EntitySlotMap, projectiles: set[EntityId]):
    for projectile in projectiles:
        index = projectile.index

        px = slots.px[index]
        py = slots.py[index]
        rad = slots.collider_radius[index]
        color = slots.color[index]

        rl.draw_polygon(rl.Vector2(px, py), 3, rad, 0, color)


def main():
    target_fps = 60
    max_entities = 2048

    rl.init_window(INIT_WIDTH, INIT_HEIGHT, "SoAsteroids")
    rl.set_target_fps(60)

    world = World(target_fps, max_entities)
    for _ in range(250):
        world.create_enemy(
            random.randrange(0, INIT_WIDTH),
            random.randrange(0, INIT_HEIGHT),
        )

    # spawn player last so it's always on top
    # we don't have z buffering
    world.create_player(INIT_WIDTH / 2, INIT_HEIGHT / 2)

    while not rl.window_should_close():
        # =======
        # UPDATE
        # =======

        # update world
        world.update()

        # update systems
        update_movement(world.slots, world.entities, world.dt)
        update_weapon(world, world.slots, world.entities)

        update_bhv_projectile(world, world.slots, world.bhv_projectile)
        update_bhv_player(world, world.slots, world.bhv_player)
        update_bhv_enemy(world.physics_system, world.slots, world.bhv_enemy, world.dt)

        # =====
        # DRAW
        # =====
        rl.begin_drawing()
        rl.clear_background(rl.BLACK)

        draw_player(world.slots, world.bhv_player)
        draw_projectile(world.slots, world.bhv_projectile)
        draw_enemy(world.slots, world.bhv_enemy)

        offset_y = 0
        rl.draw_fps(0, offset_y)

        rl.end_drawing()
    rl.close_window()


if __name__ == "__main__":
    main()
