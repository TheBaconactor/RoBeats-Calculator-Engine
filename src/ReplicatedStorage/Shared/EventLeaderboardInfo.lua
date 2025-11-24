-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:10 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.GuildRank)
require(game.ReplicatedStorage.Shared.GuildUtil)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_6 = {
    ["MemberInfo"] = {},
    ["State"] = {
        ["Active"] = 0,
        ["Closing"] = 1,
        ["Ended"] = 2
    }
}
v_u_6.MemberInfo.new = function(_, p_u_7, p_u_8) --[[ Name: new ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_5 ]]
    v_u_2:is_int(p_u_7)
    v_u_2:is_string(p_u_8)
    local v_u_9 = 0
    local v_u_10 = 0
    local v_u_11 = 1
    local v_u_12 = 0
    local v_u_13 = false
    local l_Normal_0 = v_u_5.Normal
    local v20 = {
        ["get_best_score"] = function(_) --[[ Name: get_best_score ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end,
        ["get_best_score_gear_multiplier"] = function(_) --[[ Name: get_best_score_gear_multiplier ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10;
        end,
        ["get_place"] = function(_) --[[ Name: get_place ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end,
        ["get_attempts"] = function(_) --[[ Name: get_attempts ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            return v_u_12;
        end,
        ["has_claimed_reward"] = function(_) --[[ Name: has_claimed_reward ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return v_u_13;
        end,
        ["get_audiomod"] = function(_) --[[ Name: get_audiomod ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): l_Normal_0 ]]
            return l_Normal_0;
        end,
        ["set_place"] = function(_, p14) --[[ Name: set_place ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11 = p14
        end,
        ["set_audiomod"] = function(_, p15) --[[ Name: set_audiomod ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): l_Normal_0 ]]
            l_Normal_0 = p15
        end,
        ["update_play_with_score_and_gear_power"] = function(_, p16, p17, p18) --[[ Name: update_play_with_score_and_gear_power ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): l_Normal_0, (ref 4): v_u_12 ]]
            local v19
            if v_u_9 < p16 then
                v19 = true
                v_u_9 = p16
                v_u_10 = p17
                l_Normal_0 = p18
            else
                v19 = false
            end;
            v_u_12 = v_u_12 + 1
            return v19;
        end,
        ["claim_reward"] = function(_) --[[ Name: claim_reward ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            v_u_13 = true
        end
    }
    v20.get_rbxid = function(_) --[[ Name: get_rbxid ]] --[[ Line: 28 ]]
        --[[ Upvalues: (ref 1): p_u_7 ]]
        return p_u_7;
    end;
    v20.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 29 ]]
        --[[ Upvalues: (ref 1): p_u_8 ]]
        return p_u_8;
    end;
    v20.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): p_u_7, (ref 2): p_u_8, (ref 3): v_u_9, (ref 4): v_u_10, (ref 5): v_u_11, (ref 6): v_u_12, (ref 7): l_Normal_0 ]]
        return {
            ["Id"] = p_u_7,
            ["Name"] = p_u_8,
            ["Score"] = v_u_9,
            ["GearMultiplier"] = v_u_10,
            ["Place"] = v_u_11,
            ["Attempts"] = v_u_12,
            ["AudioMod"] = l_Normal_0
        };
    end;
    v20.load_from_table = function(p21, p22) --[[ Name: load_from_table ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): p_u_7, (ref 2): p_u_8, (ref 3): v_u_9, (ref 4): v_u_10, (ref 5): v_u_11, (ref 6): v_u_12, (ref 7): l_Normal_0 ]]
        p_u_7 = p22.Id
        p_u_8 = p22.Name
        v_u_9 = p22.Score
        v_u_10 = p22.GearMultiplier
        v_u_11 = p22.Place
        v_u_12 = p22.Attempts
        l_Normal_0 = p22.AudioMod
        return p21;
    end;
    return v20;
end;
v_u_6.MemberInfo.from_table = function(_, p23) --[[ Name: from_table ]] --[[ Line: 82 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    return v_u_6.MemberInfo:new(0, ""):load_from_table(p23);
end;
v_u_6.new = function(_) --[[ Name: new ]] --[[ Line: 92 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_6, (copy 4): v_u_4 ]]
    local v24 = {}
    local v_u_25 = v_u_1:new()
    local v_u_26 = v_u_3:invalid_songkey()
    local v_u_27 = 0
    local v_u_28 = 0
    local l_Active_0 = v_u_6.Active
    v24.get_member_places = function(_) --[[ Name: get_member_places ]] --[[ Line: 101 ]]
        --[[ Upvalues: (copy 1): v_u_25 ]]
        return v_u_25;
    end;
    v24.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 102 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    v24.get_time_remaining = function(_) --[[ Name: get_time_remaining ]] --[[ Line: 103 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    v24.get_closing_time_remaining = function(_) --[[ Name: get_closing_time_remaining ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28;
    end;
    v24.get_state = function(_) --[[ Name: get_state ]] --[[ Line: 105 ]]
        --[[ Upvalues: (ref 1): l_Active_0 ]]
        return l_Active_0;
    end;
    v24.set_song_key = function(_, p29) --[[ Name: set_song_key ]] --[[ Line: 107 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26 = p29
    end;
    v24.set_time_remaining = function(_, p30) --[[ Name: set_time_remaining ]] --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        v_u_27 = p30
    end;
    v24.set_closing_time_remaining = function(_, p31) --[[ Name: set_closing_time_remaining ]] --[[ Line: 109 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        v_u_28 = p31
    end;
    v24.set_state = function(_, p32) --[[ Name: set_state ]] --[[ Line: 110 ]]
        --[[ Upvalues: (ref 1): l_Active_0 ]]
        l_Active_0 = p32
    end;
    v24.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 112 ]]
        --[[ Upvalues: (copy 1): v_u_25, (ref 2): v_u_26, (ref 3): v_u_27, (ref 4): v_u_28, (ref 5): l_Active_0 ]]
        local v33 = {}
        for v34 = 1, v_u_25:count() do
            v33[#v33 + 1] = v_u_25:get(v34):to_table()
        end;
        return {
            ["MemberPlaces"] = v33,
            ["SongKey"] = v_u_26,
            ["TimeRemaining"] = v_u_27,
            ["ClosingTimeRemaining"] = v_u_28,
            ["State"] = l_Active_0
        };
    end;
    local function f_sort_members() --[[ Name: sort_members ]] --[[ Line: 126 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_25 ]]
        v_u_1:sort_fast(v_u_25, function(p35, p36) --[[ Line: 127 ]]
            return p35:get_best_score() > p36:get_best_score();
        end)
        for v37, v38 in v_u_25:key_itr() do
            v38:set_place(v37)
        end;
    end;
    v24.remove_member_rbxid = function(_, p_u_39) --[[ Name: remove_member_rbxid ]] --[[ Line: 141 ]]
        --[[ Upvalues: (copy 1): v_u_25, (copy 2): f_sort_members ]]
        v_u_25:remove_if(function(p40) --[[ Line: 142 ]]
            --[[ Upvalues: (copy 1): p_u_39 ]]
            return p40:get_rbxid() == p_u_39;
        end)
        f_sort_members()
    end;
    v24.add_member_play = function(_, p41, p42, p43, p44, p45) --[[ Name: add_member_play ]] --[[ Line: 148 ]]
        --[[ Upvalues: (copy 1): v_u_25, (ref 2): v_u_6, (copy 3): f_sort_members ]]
        local v46 = nil
        for _, v47 in v_u_25:key_itr() do
            if v47:get_rbxid() == p41 then
                v46 = v47
                break;
            end;
        end;
        if v46 == nil then
            v46 = v_u_6.MemberInfo:new(p41, p42)
            v46:set_audiomod(p45)
            v_u_25:push_back(v46)
        end;
        local v48 = v46:update_play_with_score_and_gear_power(p43, p44, p45)
        f_sort_members()
        return v48, v46:get_place();
    end;
    v24.add_members_from_table = function(_, p49) --[[ Name: add_members_from_table ]] --[[ Line: 167 ]]
        --[[ Upvalues: (copy 1): v_u_25, (ref 2): v_u_6 ]]
        for _, v50 in pairs(p49.MemberPlaces) do
            v_u_25:push_back(v_u_6.MemberInfo:from_table(v50))
        end;
    end;
    v24.update = function(p51, p52) --[[ Name: update ]] --[[ Line: 173 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_4 ]]
        if p51:get_state() == v_u_6.State.Active then
            p51:set_time_remaining(p51:get_time_remaining() - v_u_4:TimescaleToDeltaTime(p52))
            if p51:get_time_remaining() <= 0 then
                p51:set_state(v_u_6.State.Closing)
                return;
            end;
        elseif p51:get_state() == v_u_6.State.Closing then
            p51:set_closing_time_remaining(p51:get_closing_time_remaining() - v_u_4:TimescaleToDeltaTime(p52))
            if p51:get_closing_time_remaining() <= 0 then
                p51:set_state(v_u_6.State.Ended)
            end;
        end;
    end;
    return v24;
end;
v_u_6.from_table = function(_, p53) --[[ Name: from_table ]] --[[ Line: 190 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    local v54 = v_u_6:new()
    v54:set_song_key(p53.SongKey)
    v54:set_time_remaining(p53.TimeRemaining)
    v54:set_closing_time_remaining(p53.ClosingTimeRemaining)
    v54:set_state(p53.State)
    v54:add_members_from_table(p53)
    return v54;
end;
return v_u_6;
