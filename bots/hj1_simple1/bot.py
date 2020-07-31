
__author__ = '박현수 (hspark8312@ncsoft.com), NCSOFT Game AI Lab'

import time

import sc2
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.buff_id import BuffId


class Bot(sc2.BotAI):
    """
    해병 5, 의료선 1 빌드오더를 계속 실행하는 봇
    해병은 적 사령부와 유닛중 가까운 목표를 향해 각자 이동
    적 유닛또는 사령부까지 거리가 15미만이 될 경우 스팀팩 사용
    스팀팩은 체력이 50% 이상일 때만 사용가능
    의료선은 가장 가까운 체력이 100% 미만인 해병을 치료함
    """
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.build_order = list() # 생산할 유닛 목록

    def on_start(self):
        """
        새로운 게임마다 초기화
        """
        self.build_order = list()
        self.evoked = dict()

    async def on_step(self, iteration: int):       
        actions = list()
        #
        # 빌드 오더 생성
        # 수정
        marines = self.units(UnitTypeId.MARINE)
        
        if marines.amount < 10:
            for _ in range(5):
                self.build_order.append(UnitTypeId.MARINE)
            self.build_order.append(UnitTypeId.MARAUDER)
            self.build_order.append(UnitTypeId.MEDIVAC)

        else :
            if self.minerals > 400 and self.vespene > 300:
                self.build_order.append(UnitTypeId.BATTLECRUISER)
        
            if self.minerals > 300 and self.vespene > 200:
                self.build_order.append(UnitTypeId.THOR)

            if self.minerals > 150 and self.vespene > 125:
                self.build_order.append(UnitTypeId.SIEGETANK)

        #
        # 사령부 명령 생성
        #
        ccs = self.units(UnitTypeId.COMMANDCENTER)  # 전체 유닛에서 사령부 검색
        ccs = ccs.idle  # 실행중인 명령이 없는 사령부 검색
        if ccs.exists:  # 사령부가 하나이상 존재할 경우
            cc = ccs.first  # 첫번째 사령부 선택
            if self.can_afford(self.build_order[0]) and self.time - self.evoked.get((cc.tag, 'train'), 0) > 1.0:
                # 해당 유닛 생산 가능하고, 마지막 명령을 발행한지 1초 이상 지났음
                actions.append(cc.train(self.build_order[0]))  # 첫 번째 유닛 생산 명령 
                del self.build_order[0]  # 빌드오더에서 첫 번째 유닛 제거
                self.evoked[(cc.tag, 'train')] = self.time

        #
        # 해병 명령 생성
        #

        combat_units = self.units.exclude_type([UnitTypeId.COMMANDCENTER, UnitTypeId.MEDIVAC])

          # 해병 검색
        '''for marine in marines:
            enemy_cc = self.enemy_start_locations[0]  # 적 시작 위치
            enemy_unit = self.enemy_start_locations[0]
            if self.known_enemy_units.exists:
                enemy_unit = self.known_enemy_units.closest_to(marine)  # 가장 가까운 적 유닛'''

        tanks = self.units(UnitTypeId.SIEGETANK)  # 해병 검색
        cruisers = self.units(UnitTypeId.BATTLECRUISER)
        thors = self.units(UnitTypeId.THOR)

        for unit in combat_units:
            enemy_cc = self.enemy_start_locations[0]  # 적 시작 위치
            enemy_unit = self.enemy_start_locations[0]
            if self.known_enemy_units.exists:
                enemy_unit = self.known_enemy_units.closest_to(unit) 

            # 적 사령부와 가장 가까운 적 유닛중 더 가까운 것을 목표로 공격 명령 생성
            if unit.distance_to(enemy_cc) < unit.distance_to(enemy_unit):
                target = enemy_cc
            else:
                target = enemy_unit

            if combat_units.amount > 15:
                    # 전투가능한 유닛 수가 15를 넘으면 적 본진으로 공격
                actions.append(unit.attack(target))
                use_stimpack = True
            else:
                    # 적 사령부 방향에 유닛 집결
                target = self.start_location + 0.25 * (enemy_cc.position - self.start_location)
                actions.append(unit.attack(target))
                use_stimpack = False

            if unit.type_id in (UnitTypeId.MARINE, UnitTypeId.MARAUDER):
                if use_stimpack and unit.distance_to(target) < 15:
                        # 유닛과 목표의 거리가 15이하일 경우 스팀팩 사용
                    if not unit.has_buff(BuffId.STIMPACK) and unit.health_percentage > 0.5:
                            # 현재 스팀팩 사용중이 아니며, 체력이 50% 이상
                        if self.time - self.evoked.get((unit.tag, AbilityId.EFFECT_STIM), 0) > 1.0:
                                # 1초 이전에 스팀팩을 사용한 적이 없음
                            actions.append(unit(AbilityId.EFFECT_STIM))
                            self.evoked[(unit.tag, AbilityId.EFFECT_STIM)] = self.time

        #
        # 의료선 명령 생성
        #
        medivacs = self.units(UnitTypeId.MEDIVAC)  # 의료선 검색
        wounded_units = marines.filter(lambda u: u.health_percentage < 1.0)  # 체력이 100% 이하인 유닛 검색
        for medivac in medivacs:
            if wounded_units.exists:
                wounded_unit = wounded_units.closest_to(medivac)  # 가장 가까운 체력이 100% 이하인 유닛
                actions.append(medivac(AbilityId.MEDIVACHEAL_HEAL, wounded_unit))  # 유닛 치료 명령

        await self.do_actions(actions)

