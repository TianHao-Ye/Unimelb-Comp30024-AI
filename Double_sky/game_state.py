from referee.game import _SET_HEXES, _HEX_STEPS, _BEATS_WHAT, _WHAT_BEATS
import math

class Game_state:  
    def __init__(self):
        self.MAX_THROW = 9
        self.MAX_TURN = 360
        self.board = {x: [] for x in _SET_HEXES}
        self.turn = 0
        self.throws = {"upper": 0, "lower": 0}
        self.tokens = {"upper": {"s": [], "p": [], "r": []},"lower": {"s": [], "p": [], "r": []}}
    
    def battle(self, hex):
        symbols = self.board[hex]
        types = {s.lower() for s in symbols}
        if len(types) == 1:
            # no fights
            self.update_toekns_on_board(hex, None, symbols)
        if len(types) == 3:
            # everyone dies
            self.update_toekns_on_board(hex, symbols, None)
            
        # else there are two, only some die:
        else:
            defeated = []
            for t in types:        
                for s in symbols:
                    if(_BEATS_WHAT[t] == s.lower()):
                        defeated.append(s)
            
            survived = [x for x in symbols if x not in defeated]
            self.update_toekns_on_board(hex, defeated, survived)
        
    def update_toekns_on_board(self, hex, defeated, survived):
        if(defeated):
            for s in defeated:
                if(s.isupper()):
                    self.tokens["upper"][s.lower()].remove(hex)
                else:
                    self.tokens["lower"][s].remove(hex)
        if(survived):
            self.board[hex] = survived
    
    def test_operation(self, colour, operation):
        self.turn += 1
        role_case = str.lower if colour == "lower" else str.upper
        battles = []
        atype, *aargs = operation
        if atype == "THROW":
            s, x = aargs
            self.board[x].append(s.upper() if colour == "upper" else s.lower())
            self.throws[colour] += 1
            self.tokens[colour][s].append(x)
            battles.append(x)
        else:
            x, y = aargs
            s = list(map(role_case, self.board[x][0]))[0]
            self.board[x].remove(s)
            self.board[y].append(s)
            self.tokens[colour][s.lower()].remove(x)
            self.tokens[colour][s.lower()].append(y)
            battles.append(y)
        for x in battles:
            self.battle(x)    
                    
    def update_state(self, player_colour, opponent_action, player_action):
        self.turn += 1
        opponent_colour = "upper" if player_colour == "lower" else "lower"
        player_case = str.lower if player_colour == "lower" else str.upper
        opponent_case = str.lower if player_colour == "upper" else str.upper
        battles = []
        atype, *aargs = player_action
        if atype == "THROW":
            s, x = aargs
            self.board[x].append(s.upper() if player_colour == "upper" else s.lower())
            self.throws[player_colour] += 1
            self.tokens[player_colour][s].append(x)
            battles.append(x)
        else:
            x, y = aargs
            s = list(map(player_case, self.board[x][0]))[0]
            self.board[x].remove(s)
            self.board[y].append(s)
            self.tokens[player_colour][s.lower()].remove(x)
            self.tokens[player_colour][s.lower()].append(y)
            battles.append(y)
            
        atype, *aargs = opponent_action
        if atype == "THROW":
            s, x = aargs
            self.board[x].append(s.upper() if opponent_colour == "upper" else s.lower())
            self.throws[opponent_colour] += 1
            self.tokens[opponent_colour][s].append(x)
            battles.append(x)
        else:
            x, y = aargs
            s = list(map(opponent_case, self.board[x][0]))[0]
            self.board[x].remove(s)
            self.board[y].append(s)
            self.tokens[opponent_colour][s.lower()].remove(x)
            self.tokens[opponent_colour][s.lower()].append(y)
            battles.append(y)
        
        for x in battles:
            self.battle(x) 
    
    def available_actions(self, colour):
        operations = []
        operations += self.available_throws(colour)
        occupied = [i for sublist in self.tokens[colour].values() for i in sublist]
        for x in occupied:
            operations += self.available_moves(colour, x)
        return operations
    
    def available_throws(self, colour):
        operations = []
        if self.throws[colour] < 9:
            throw_zone = [hex for hex in _SET_HEXES if self.in_throwable_area(hex, colour)]            
            for x in throw_zone:
                for s in "rps":
                    operations.append(("THROW", s, x))
        return operations
    
    def in_throwable_area(self, hex, colour):
        """
        detect whether r coordinate within colour's throwable area
        """
        throws = self.throws[colour]
        sign = -1 if colour == "lower" else 1
        return sign * hex[0] >= 4 - throws
    
    def available_moves(self, colour, x):
        """
        return x's next available slides and swings
        """
        operations = []
        occupied = [i for sublist in self.tokens[colour].values() for i in sublist]
        adjacent_x = self.adjacent_hex(x)
        for y in adjacent_x:
            operations.append(("SLIDE", x, y))
            if(y in occupied):
                opposite_y = self.adjacent_hex(y) - adjacent_x - {x}
                for z in opposite_y:
                    operations.append(("SWING", x, z))  
        return operations
    
    def is_excess_throw(self, colour, operation):
        """
        manually detect whether throw type self tokens on board relative to defeatable opponent tokens is too much (>=2), 
                 and difference of throw action remaining not excess 2
        """
        oppo_colour = "upper" if colour == "lower" else "lower"
        atype, s, y = operation
        self_type_hexes = self.tokens[colour][s]
        defeatable_oppo_type = _BEATS_WHAT[s]
        oppo_type_hexes = self.tokens[oppo_colour][defeatable_oppo_type]
        self_remaining = 9 - self.throws[colour]
        oppo_remaining = 9 - self.throws[oppo_colour]
        if self_remaining - oppo_remaining <= -2:
            return True
        if len(self_type_hexes) - len(oppo_type_hexes) >=2:
            return True
        
        return False
    
    def is_reasonable_throw(self, colour, operation):
        """
        return whether operation is reasonable throw
        case 1: first turn, must throw
        case 2: potentially aggressive throw on oppo's hex next possible hexes
        case 3: if oppo hex not in throwable area, throw on closest hex in throwable area is reasonable
        """
        oppo_colour = "upper" if colour == "lower" else "lower"
        oppo_tokens = self.tokens[oppo_colour]
        atype, *aargs = operation
        if atype != "THROW":
            return False
        s, x = aargs
        # case 1
        if self.turn == 0:
            return True
        for oppo_type in oppo_tokens:
            oppo_hexes = oppo_tokens[oppo_type]
            # for every current opponent token
            for oppo_hex in oppo_hexes:
                # find its next possible moves
                oppo_next_operations = self.available_moves(oppo_colour, oppo_hex)
                # next reasonable hexes + static hex
                oppo_next_hexes = [y for atype, x, y in oppo_next_operations] + [oppo_hex]
                throw_type  = _WHAT_BEATS[oppo_type]
                # case 2
                if(throw_type == s and x in oppo_next_hexes):
                    return True
                # case 3
                if(not self.in_throwable_area(oppo_hex, colour)):
                    if(throw_type == s and x in self.closest_throwable_hexes(colour, oppo_hex)):
                        return True
                    
        return False
    
    def is_def_throw(self, colour, operation):
        oppo_colour = "upper" if colour == "lower" else "lower"
        oppo_tokens = self.tokens[oppo_colour]
        atype, s, x = operation
        for oppo_type in oppo_tokens:
            oppo_hexes = oppo_tokens[oppo_type]
            # for every current opponent token
            for oppo_hex in oppo_hexes:
                # find its next possible moves
                oppo_next_operations = self.available_moves(oppo_colour, oppo_hex)
                oppo_next_hexes = []
                # next reasonable hexes + static hex
                for oppo_o in oppo_next_operations:
                    if self.is_agg_move(oppo_colour, oppo_o) and\
                        (self.agg_move_distance(oppo_colour, oppo_o) == 2 or\
                         self.agg_move_distance(oppo_colour, oppo_o) == 1):
                        oppo_next_hexes.append(oppo_o[2])      
                throw_type  = _WHAT_BEATS[oppo_type]
                # case 2
                if(throw_type == s and x in oppo_next_hexes):
                    return True
        
    def if_stategic_throw(self, colour, operation):
        oppo_colour = "upper" if colour == "lower" else "lower"
        oppo_tokens = self.tokens[oppo_colour]
        atype, s, x = operation
        for oppo_type in oppo_tokens:
            oppo_hexes = oppo_tokens[oppo_type]
            throw_type  = _WHAT_BEATS[oppo_type]
            # for every current opponent token
            for oppo_hex in oppo_hexes:
                if(not self.in_throwable_area(oppo_hex, colour)):
                    if(throw_type == s and x in self.closest_throwable_hexes(colour, oppo_hex)):
                        return True
         
    def is_agg_throw(self, colour, operation):
        """
        since opponent tokens are vulnerable to throw action, throw directly on the opponent token current hex is aggressive
        """
        oppo_colour = "upper" if colour == "lower" else "lower"
        oppo_tokens = self.tokens[oppo_colour]
        atype, s, x = operation
        for oppo_type in oppo_tokens:
            oppo_hexes = oppo_tokens[oppo_type]
            # for every current opponent token
            for oppo_hex in oppo_hexes:
                throw_type  = _WHAT_BEATS[oppo_type]
                # if operation can potentially defeat this opponent token
                if(throw_type == s and x == oppo_hex):
                    return True
    
    def closest_throwable_hexes(self, colour, oppo_hex):
        # all throwable hexes of colour
        throwable_hexes = [h for h in _SET_HEXES if self.in_throwable_area(h, colour)]
        # throwable hexes of colour
        distance_to_oppo_hex = {h: self.hex_distance(h, oppo_hex) for h in throwable_hexes}
        closest_distance = min(distance_to_oppo_hex.values())
        closest_hexes = [h for h in distance_to_oppo_hex if distance_to_oppo_hex[h] == closest_distance]
        return closest_hexes
    
    def is_agg_move(self, colour, operation):
        """
        determine whether aggressive slide or swing 
        """
        oppo_colour = "upper" if colour == "lower" else "lower"
        atype, *aargs = operation
        if atype == "THROW":
            return False
        x, y = aargs
        self_type = self.board[x][0].lower()
        oppo_type = _BEATS_WHAT[self_type]
        oppo_hexes = self.tokens[oppo_colour][oppo_type]
        # there are defeatable opponents tokens on board
        if(oppo_hexes):
            distances = {hex: self.hex_distance(x, hex) for hex in oppo_hexes}
            closest_oppo_hex = min(distances, key=distances.get)
            if(self.hex_distance(y, closest_oppo_hex) < self.hex_distance(x, closest_oppo_hex)):
                return True
        return False
    
    def agg_move_distance(self, colour, operation):
        """
        count how many steps to defeat closest opponent token
        in special case: when swing operation is able to defeat opponent token, although distance is 2, return 1 instead
        """
        oppo_colour = "upper" if colour == "lower" else "lower"
        atype, x, y = operation
        self_type = self.board[x][0].lower()
        oppo_type = _BEATS_WHAT[self_type]
        oppo_hexes = self.tokens[oppo_colour][oppo_type]
        # there are defeatable opponents tokens on board
        if(oppo_hexes):
            distances = {hex: self.hex_distance(x, hex) for hex in oppo_hexes}
            closest_oppo_hex = min(distances, key=distances.get)
            closest_oppo_distance = distances[closest_oppo_hex]
            # special case
            if closest_oppo_distance == 2 and y in oppo_hexes:
                closest_oppo_distance = 1
        return closest_oppo_distance
    
    def is_def_move(self, colour, operation):
        """
        determine whether defensive slide or swing 
        """
        oppo_colour = "upper" if colour == "lower" else "lower"
        atype, *aargs = operation
        if atype == "THROW":
            return False
        x, y = aargs
        self_type = self.board[x][0].lower()
        oppo_type = _WHAT_BEATS[self_type]
        oppo_hexes = self.tokens[oppo_colour][oppo_type]
        if(oppo_hexes):
            distances = {hex: self.hex_distance(x, hex) for hex in oppo_hexes}
            closest_oppo_hex = min(distances, key=distances.get)
            if(self.hex_distance(y, closest_oppo_hex) > self.hex_distance(x, closest_oppo_hex)):
                return True
        return False
    
    def def_move_distance(self, colour, operation):
        """
        count how many steps to be defeated by closest opponent token
        special case: opponent token at 2 step, can swing to defeat self token, return 1
        """
        oppo_colour = "upper" if colour == "lower" else "lower"
        atype, x, y = operation
        self_type = self.board[x][0].lower()
        oppo_type = _WHAT_BEATS[self_type]
        oppo_hexes = self.tokens[oppo_colour][oppo_type]
        if(oppo_hexes):
            distances = {hex: self.hex_distance(x, hex) for hex in oppo_hexes}
            closest_oppo_hex = min(distances, key=distances.get)
            closest_oppo_distance = distances[closest_oppo_hex]
            if closest_oppo_distance == 2 and bool(set(self.adjacent_hex(x)) & set(self.adjacent_hex(closest_oppo_hex))):
                closest_oppo_distance = 1

        return closest_oppo_distance               
    
    def is_suicide_operation_and_allowed(self, colour, operation):
        """
        return false if operation defeat self, and not defeat opponent
        return true  if operations 1. defeat self and defeat opponent 
                                2. not defeat self, not defeat opponent
                                3. not defeat self, defeat opponent
        """
        oppo_colour = "upper" if colour == "lower" else "lower"
        self_tokens = self.tokens[colour]
        oppo_tokens = self.tokens[oppo_colour]
        defeat_self = False
        defeat_oppo = False
        atype, *aargs = operation
        if atype == "THROW":
            s, x = aargs
            s_defeat_type = _BEATS_WHAT[s]
            s_be_defeated_by_type = _WHAT_BEATS[s]
            defeat_hexes_self = self_tokens[s_defeat_type]
            be_defeated_hexes_self = self_tokens[s_be_defeated_by_type]
            defeat_hexes_oppo = oppo_tokens[s_defeat_type]
            if x in defeat_hexes_self or x in be_defeated_hexes_self:
                defeat_self = True
            if x in defeat_hexes_oppo:
                defeat_oppo = True       
        else:
            x, y = aargs
            self_type = self.board[x][0].lower()
            s_defeat_type = _BEATS_WHAT[self_type]
            s_be_defeated_by_type = _WHAT_BEATS[self_type]
            defeat_hexes_self = self_tokens[s_defeat_type]
            be_defeated_hexes_self = self_tokens[s_be_defeated_by_type]
            defeat_hexes_oppo = oppo_tokens[s_defeat_type]
            if x in defeat_hexes_self or x in be_defeated_hexes_self:
                defeat_self = True
            if x in defeat_hexes_oppo:
                defeat_oppo = True  
        if(defeat_self and not defeat_oppo):
            return False
        else:
            return True        
                          
    def is_necess_time_to_throw(self, colour):
        """
        return whether is the necessary for colour to use throw operation at this state
        case 1: first turn, must throw
        case 2: there is opponent's token in self's throwable area
        case 3: on board, no self's tokens can defeat opponent's tokens
        case 4: in order to expand throwable area
        """
        opponent_colour = "upper" if colour == "lower" else "lower"
        oppo_tokens = self.tokens[opponent_colour]
        self_tokens = self.tokens[colour]
        no_aggresive_self_token = True
        # case 1
        if(self.turn == 0):
            return True

        for oppo_type in oppo_tokens:
            # case 2
            type_hexes = oppo_tokens[oppo_type]
            for type_hex in type_hexes:
                if self.in_throwable_area(type_hex, colour):
                    return True
                # case 3
            self_beat_oppo_type = _WHAT_BEATS[oppo_type]
            self_beat_oppo_hexes = self_tokens[self_beat_oppo_type]
            if (self_beat_oppo_hexes):
                no_aggresive_self_token = False
        # case 3
        if(no_aggresive_self_token):
            return True
        # to expand throwable area at the beginning of the game
        if self.throws[colour] < 4:
            return True
        
        return False            
        
    def no_target_on_board(self, colour):
        """
        return whether colour's token on board are objectiveless
        """
        oppo_colour = "upper" if colour == "lower" else "lower"
        oppo_tokens = self.tokens[oppo_colour]
        
        for type in oppo_tokens:
            if(oppo_tokens[type]):
                return False
        return True
           
    def operation_refining(self, colour, ops):
        # print("before refining len")
        # print(len(ops))
        filtered_ops = self.reasonable_filter(colour, ops)
        reordered_ops = self.goal_directed_reordering(colour, filtered_ops)
        # print("after refining len")
        # print(len(reordered_ops))
        # print("******************")
        return reordered_ops
    
    def goal_directed_reordering(self, colour, ops):
        """
        priority:
        1. one step aggressive move
        2. one step defensive move
        3. aggressive throw
        4. two steps aggressive move 
        5. two steps defensive move
        6. reasonable throw
        7. the rest moves, either in oppo's throwable area or not
        # 7. moves within opponent's throwable area
        # 8. moves outside opponent's throwable area, sorting them based on distance to thier opponent
        special case: ops are all non-reasonable movings due to lack of opponent tokens
        """
        oppo_colour = "upper" if colour == "lower" else "lower"
        reordered_ops = []
        reordered_ops += [o for o in ops if self.is_agg_move(colour, o) and self.agg_move_distance(colour, o) == 1]
        reordered_ops += [o for o in ops if self.is_def_move(colour, o) and self.def_move_distance(colour, o) == 1 and o not in reordered_ops]
        reordered_ops += [o for o in ops if self.is_reasonable_throw(colour, o) and self.is_agg_throw(colour, o) and o not in reordered_ops]
        reordered_ops += [o for o in ops if self.is_agg_move(colour, o) and self.agg_move_distance(colour, o) == 2 and o not in reordered_ops]
        reordered_ops += [o for o in ops if self.is_def_move(colour, o) and self.def_move_distance(colour, o) == 2 and o not in reordered_ops]
        reordered_ops += [o for o in ops if self.is_reasonable_throw(colour, o) and self.is_def_throw(colour, o) and o not in reordered_ops]
        if (len([o for o in reordered_ops if o[0] == "THROW"]) == 0):
            reordered_ops += [o for o in ops if self.is_reasonable_throw(colour, o) and self.if_stategic_throw(colour, o) and o not in reordered_ops]
        # reordered_ops += [(atype, x, y) for (atype, x, y) in ops if (atype != "THROW") and (self.in_throwable_area(x, oppo_colour)) and ((atype, x, y) not in reordered_ops)]
        the_rest = [o for o in ops if o not in reordered_ops]
        the_sorted_rest = self.further_ordering_pruning(colour, the_rest)
        reordered_ops += [o for o in the_sorted_rest if o not in reordered_ops]
        #special case
        if not reordered_ops:
            limit = (int)(len(ops)/3)
            reordered_ops = ops[:limit]
        return reordered_ops
    
    def further_ordering_pruning(self, colour, ops):
        the_rest_limit = 4
        attack_distance = {o:self.agg_move_distance(colour, o) for o in ops if self.is_agg_move(colour, o)}
        defense_distance = {o:self.def_move_distance(colour, o) for o in ops if self.is_def_move(colour, o)}
        # removing conflicting operation wrt distance
        for o in attack_distance.copy():
            if o in defense_distance:
                if attack_distance[o] <=defense_distance[o]:
                    del defense_distance[o]
                else:
                    del attack_distance[o]
        attack_distance.update(defense_distance)
        # sort dict based on distance, ascending  
        sorted_ops = sorted(attack_distance.keys(), key=lambda x:x[1])
        if(len(sorted_ops) >= the_rest_limit):
            limit = (int)(len(sorted_ops)/3)
            sorted_ops = sorted_ops[:limit]
        return sorted_ops
    
    
    def reasonable_filter(self, colour, ops):
        opponent_colour = "upper" if colour == "lower" else "lower"
        reasonable_ops = []
        ops = [o for o in ops if self.is_suicide_operation_and_allowed(colour, o)]
        for o in ops:
            if o[0] == "THROW":
                if(not self.is_necess_time_to_throw(colour)):
                    pass
                elif self.no_target_on_board(opponent_colour):
                    if self.is_reasonable_throw(colour, o):
                        reasonable_ops.append(o)
                else:
                    if self.is_reasonable_throw(colour, o) and not self.is_excess_throw(colour, o):
                        reasonable_ops.append(o)
            else:
                # if no target on board, all available moves added
                if self.no_target_on_board(colour):
                    reasonable_ops.append(o)
                # else, only aggressive moves and defensive added
                elif self.is_agg_move(colour, o) or self.is_def_move(colour, o):
                    reasonable_ops.append(o)
        if(not reasonable_ops):
            reasonable_ops = ops
        return reasonable_ops
    
    def closest_defeating_distance(self, colour):
        oppo_colour = "upper" if colour == "lower" else "lower"
        self_tokens = self.tokens[colour]
        oppo_tokens = self.tokens[oppo_colour]
        c_d_self_defeat_oppo = +math.inf
        for self_type in self_tokens:
            self_hexes = self_tokens[self_type]
            oppo_type = _BEATS_WHAT[self_type]
            oppo_hexes = oppo_tokens[oppo_type]
            # there is defeatable relationship
            if(self_hexes and oppo_hexes):
                for self_hex in self_hexes:
                    for oppo_hex in oppo_hexes:
                        distance = self.hex_distance(self_hex, oppo_hex)
                        c_d_self_defeat_oppo = min(c_d_self_defeat_oppo, distance)
        return c_d_self_defeat_oppo
    
    def hex_distance(self, a, b):
        return (abs(a[0] - b[0]) 
          + abs(a[0] + a[1] - b[0] - b[1])
          + abs(a[1] - b[1])) / 2
             
    def adjacent_hex(self, x):
        rx, qx = x
        return _SET_HEXES & {(rx + ry, qx + qy) for ry, qy in _HEX_STEPS}
    