-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
return {
    ["ClientJoinTargetLeavePenalizedFail"] = "MatchLeavePenalty.ClientJoinTargetLeavePenalizedFail",
    ["ClientEnqueueLeavePenalizedFail"] = "MatchLeavePenalty.ClientEnqueueLeavePenalizedFail",
    ["on_leave_apply_penalty_for_playerblob"] = function(_, p3) --[[ Name: on_leave_apply_penalty_for_playerblob ]] --[[ Line: 9 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        v_u_1:set_matches_left(p3, v_u_1:get_matches_left(p3) + 1)
        v_u_1:set_just_left_match(p3, true)
    end,
    ["on_startup_apply_just_left_match_penalty_for_playerblob"] = function(_, p4, p5) --[[ Name: on_startup_apply_just_left_match_penalty_for_playerblob ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        v_u_1:set_just_left_match(p4, false)
        local v6 = v_u_1:get_matches_left(p4)
        local v7 = true
        local v8
        if v6 <= 1 then
            v8 = 0
            v7 = false
        elseif v6 == 2 then
            v8 = 300
        elseif v6 == 3 then
            v8 = 600
        elseif v6 == 4 then
            v8 = 1200
        else
            v8 = 1800
        end;
        v_u_1:set_match_leave_penalty_end_time(p4, p5 + v8)
        return v7, v8;
    end,
    ["get_required_productid_to_clear_penalty"] = function(_, p9, p10) --[[ Name: get_required_productid_to_clear_penalty ]] --[[ Line: 41 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v11 = v_u_1:get_match_leave_penalty_end_time(p9) - p10
        if v11 <= 0 then
            return v_u_2.ProductID_None;
        elseif v11 <= 300 then
            return v_u_2.ProductID_LeavePenaltyClear5;
        elseif v11 <= 600 then
            return v_u_2.ProductID_LeavePenaltyClear10;
        else
            return v_u_2.ProductID_LeavePenaltyClear30;
        end;
    end,
    ["is_correct_productid"] = function(_, p12, p13, p14) --[[ Name: is_correct_productid ]] --[[ Line: 54 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v15 = v_u_1:get_match_leave_penalty_end_time(p12) - p13
        if v15 <= 0 then
            return (p14 == v_u_2.ProductID_None or (p14 == v_u_2.ProductID_LeavePenaltyClear5 or p14 == v_u_2.ProductID_LeavePenaltyClear10)) and true or p14 == v_u_2.ProductID_LeavePenaltyClear30;
        elseif v15 <= 300 then
            return (p14 == v_u_2.ProductID_LeavePenaltyClear5 or p14 == v_u_2.ProductID_LeavePenaltyClear10) and true or p14 == v_u_2.ProductID_LeavePenaltyClear30;
        elseif v15 <= 600 then
            return p14 == v_u_2.ProductID_LeavePenaltyClear10 and true or p14 == v_u_2.ProductID_LeavePenaltyClear30;
        else
            return p14 == v_u_2.ProductID_LeavePenaltyClear30;
        end;
    end,
    ["productid_is_clear_match_leave_penalty"] = function(_, p16) --[[ Name: productid_is_clear_match_leave_penalty ]] --[[ Line: 67 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        return (p16 == v_u_2.ProductID_LeavePenaltyClear5 or p16 == v_u_2.ProductID_LeavePenaltyClear10) and true or p16 == v_u_2.ProductID_LeavePenaltyClear30;
    end,
    ["get_buy_penalty_clear_message_for_name_and_productid"] = function(_, p17, p18) --[[ Name: get_buy_penalty_clear_message_for_name_and_productid ]] --[[ Line: 73 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        if p18 == v_u_2.ProductID_LeavePenaltyClear5 then
            return string.format("\"%s\" is sorry they left a match in progress. They promise it won\'t happen again!", p17);
        elseif p18 == v_u_2.ProductID_LeavePenaltyClear10 then
            return string.format("\"%s\" is REALLY sorry they left a match in progress. Again. Did they learn their lesson this time?", p17);
        else
            return string.format("\"%s\" is really REALLY sorry they left (yet another) match in progress. Someone PLEASE tell them to cut it out.", p17);
        end;
    end
};
