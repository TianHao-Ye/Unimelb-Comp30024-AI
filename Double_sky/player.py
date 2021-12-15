from referee.game import _SET_HEXES, _HEX_STEPS, _BEATS_WHAT, _WHAT_BEATS
from Double_sky.game_state import Game_state
import copy, math

        
        
class Player:
    def __init__(self, player):

        self.colour = player
        self.opponent_colour = "lower" if player == "upper" else "upper"
        self.game_state = Game_state()
          
    def action(self):
        return self.minimax_decision()
    
    def update(self, opponent_action, player_action): 
        self.game_state.update_state(self.colour, opponent_action, player_action) 
    
    def minimax_value(self, state, depth, alpha, beta, max_turn):
        """
        alpha is the worst decision value of maximizer (the larger, the better)
        beta if the worst decision value of minimizer (the smaller, the better)
        """
        if(self.cut_off_test(state, depth)):
            return self.evaluate(state)
        
        if(max_turn):
            max_eval = -math.inf
            operations = state.available_actions(self.colour)
            operations = state.operation_refining(self.colour, operations)
            for operation in operations:
                child_state  = copy.deepcopy(state)
                child_state.test_operation(self.colour, operation)
                eval_value = self.minimax_value(child_state, depth+1, alpha, beta, False)
                max_eval = max(max_eval, eval_value)
                alpha = max(alpha, eval_value)
                # means min have a better option earlier on the tree
                if beta <= alpha:
                    break
            return max_eval
        
        else:
            min_eval = math.inf
            operations = state.available_actions(self.opponent_colour)
            operations = state.operation_refining(self.opponent_colour, operations)
            for operation in operations:
                child_state  = copy.deepcopy(state)
                child_state.test_operation(self.opponent_colour, operation)
                eval_value = self.minimax_value(child_state, depth+1, alpha, beta, True)
                min_eval = min(min_eval, eval_value)
                beta = min(beta, eval_value)
                # means max have a better option earlier on the tree
                if beta <= alpha:
                    break
            return min_eval
        
    def minimax_decision(self):
        operations = self.game_state.available_actions(self.colour)
        
        operations = self.game_state.operation_refining(self.colour, operations)
        evals = {}
        for operation in operations:
            child_state =  copy.deepcopy(self.game_state)
            child_state.test_operation(self.colour, operation)
            # store max's operations and corresponding minimax value
            evals[operation] = self.minimax_value(child_state, 1, -math.inf, math.inf, False)
        return max(evals, key=evals.get)


    
    def evaluate(self, game_state):
        eval_value = 0
        features_list = [self.f1, self.f2, self.f3, self.f4, self.f5, self.f6, self.f7]
        weights = [0.3, 0.3, 0.3, 0.04, 0.02, 0.02, 0.02]
        avg_weights =  1/len(features_list)
        for i in range(len(features_list)):
            eval_value += features_list[i](game_state) *weights[i]
        return eval_value
    
    def f1(self, game_state):
        """
        difference of number of already dead token
        the smaller, the better
        """
        self_on_board = 0
        oppo_on_board = 0

        tokens = game_state.tokens
        for s in tokens[self.colour]:
            self_on_board += len(tokens[self.colour][s])
        for s in tokens[self.opponent_colour]:
            oppo_on_board += len(tokens[self.opponent_colour][s])
        self_dead = self.game_state.throws[self.colour] - self_on_board
        oppo_dead = self.game_state.throws[self.opponent_colour] - oppo_on_board
        
        return oppo_dead - self_dead
    
    def f2(self, game_state):
        """
        difference of throw operation remaining
        the larger, the better
        """
        self_remaining = game_state.MAX_THROW - game_state.throws[self.colour]
        oppo_remaining = game_state.MAX_THROW - game_state.throws[self.opponent_colour]
        return self_remaining - oppo_remaining
        
    def f3(self, game_state):
        """
        difference of closest aggressive distance (to defeat opponent)
        the smaller, the better
        """
        c_d_self_defeat_oppo = game_state.closest_defeating_distance(self.colour)
        c_d_oppo_defeat_self = game_state.closest_defeating_distance(self.opponent_colour)
        return c_d_oppo_defeat_self - c_d_self_defeat_oppo
    
    def f4(self, game_state):
        """
        difference of total distance of aggressive distance (to defeat opponent)
        the smaller the distance, the better
        """
        self_tokens = game_state.tokens[self.colour]
        oppo_tokens = game_state.tokens[self.opponent_colour]
        self_defeat_oppo = 0
        oppo_defeat_self = 0
        for self_type in self_tokens:
            self_hexes = self_tokens[self_type]
            oppo_type = _BEATS_WHAT[self_type]
            oppo_hexes = oppo_tokens[oppo_type]
            # there is defeatable relationship
            if(self_hexes and oppo_hexes):
                for self_hex in self_hexes:
                    for oppo_hex in oppo_hexes:
                        distance = game_state.hex_distance(self_hex, oppo_hex)
                        self_defeat_oppo += distance
        for oppo_type in oppo_tokens:
            oppo_hexes = oppo_tokens[oppo_type]
            self_type = _BEATS_WHAT[oppo_type]
            self_hexes = self_tokens[self_type]
            # there is defeatable relationship
            if(self_hexes and oppo_hexes):
                for oppo_hex in oppo_hexes:
                    for self_hex in self_hexes:
                        distance = game_state.hex_distance(self_hex, oppo_hex)
                        oppo_defeat_self += distance
        
        return  oppo_defeat_self - self_defeat_oppo
                      
    def f5(self, game_state):
        """
        difference of number of defeatable tokens (can be killed) on board
        the smaller, the better
        """
        tokens = game_state.tokens
        dangerous_self_token_on_board = 0
        dangerous_oppo_token_on_board = 0
        for self_type in tokens[self.colour]:
            s_number = len(tokens[self.colour][self_type])
            if(s_number != 0):
                beat_s = _WHAT_BEATS[self_type]
                beat_s_number = len(tokens[self.opponent_colour][beat_s])
                if(beat_s_number != 0):
                    dangerous_self_token_on_board += s_number
        for oppo_type in tokens[self.opponent_colour]:
            s_number = len(tokens[self.opponent_colour][oppo_type])
            if(s_number != 0):
                beat_s = _WHAT_BEATS[oppo_type]
                beat_s_number = len(tokens[self.colour][beat_s])
                if(beat_s_number != 0):
                    dangerous_oppo_token_on_board += s_number
        return dangerous_oppo_token_on_board - dangerous_self_token_on_board
    
    def f6(self, game_state):
        """
        total number of self tokens overlapping, potentially dangerous (several tokens defeated by opponent at one time)
        closer to 0, the better
        """
        total_overlapping =0
        self_tokens = game_state.tokens[self.colour]
        for type in self_tokens:
            hexes = self_tokens[type]
            token_number_on_hex = {h: hexes.count(h) for h in hexes}
            token_numbers = token_number_on_hex.values()
            if(token_numbers):
                for number in token_numbers:
                    if(number >1):
                        overlap = number - 1
                        total_overlapping += overlap
        return total_overlapping * -4
    
    def f7(self, game_state):
        """
        the position of self tokens,
        in corner, only 3 possible moves
        in border, only 4 possible moves
        in middle, 6 possible moves
        
        return number of token in corner or in border, the lesser, the better
        """
        token_corner_border = 0
        TOKEN_CORNER = [(4, -4), (4, 0), (-4, 0), (-4, 4)]
        TOKEN_BORDER = [(4, -3), (4, -2), (4, -1), (3, 1), (2, 2), (1, 3),
                        (-1, 4), (-2, 4), (-3, 4), (-4, 1), (-4, 2), (-4, 3),
                        (-1, -3), (-2, -2), (-3, -1), (1, -4), (2, -4), (3, -4)]
        self_token = game_state.tokens[self.colour]
        for hexes in self_token.values():
            for hex in hexes:
                if hex in TOKEN_CORNER or hex in TOKEN_BORDER:
                    token_corner_border +=1
        return token_corner_border * -1
    
    def cut_off_test(self, state, cur_depth):
        limit_depth = 3
        if(cur_depth == limit_depth):
            return True
        if(self.terminal_test(state)):
            return True
        return False
        
    def terminal_test(self, state):
        up_throws = state.MAX_THROW - state.throws["upper"]
        up_tokens = [
            s.lower() for x in state.board.values() for s in x if s.isupper()
        ]
        up_symset = set(up_tokens)
        lo_throws = state.MAX_THROW - state.throws["lower"]
        lo_tokens = [
            s for x in state.board.values() for s in x if s.islower()
        ]
        lo_symset = set(lo_tokens)
        up_invinc = [
            s for s in up_symset
            if (lo_throws == 0) and (_WHAT_BEATS[s] not in lo_symset)
        ]
        lo_invinc = [
            s for s in lo_symset
            if (up_throws == 0) and (_WHAT_BEATS[s] not in up_symset)
        ]
        
        up_notoks = (up_throws == 0) and (len(up_tokens) == 0)
        lo_notoks = (lo_throws == 0) and (len(lo_tokens) == 0)
        up_onetok = (up_throws == 0) and (len(up_tokens) == 1)
        lo_onetok = (lo_throws == 0) and (len(lo_tokens) == 1)

        # condition 1: one player has no remaining throws or tokens
        if up_notoks and lo_notoks:
            return True
        if up_notoks:
            return True
        if lo_notoks:
            return True

        # condition 2: both players have an invincible token
        if up_invinc and lo_invinc:
            return True

        # condition 3: one player has an invincible token, the other has
        #              only one token remaining (not invincible by 2)
        if up_invinc and lo_onetok:
            return True
        if lo_invinc and up_onetok:
            return True

        # condition 4: the players have had their 360th turn without end
        if state.turn >= state.MAX_TURN:
            return True
        return False

