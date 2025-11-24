-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:57 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.Pets.PetDatabase)
require(game.ReplicatedStorage.Avatar.GearStats)
local v7 = require(game.ReplicatedStorage.Shared.SPRange)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_28 = {
    ["AssignmentType"] = {
        ["Type1"] = 1,
        ["Type2"] = 2,
        ["Type3"] = 3
    },
    ["get_max_pets_in_assignment"] = function(_) --[[ Name: get_max_pets_in_assignment ]] --[[ Line: 50 ]]
        return 3;
    end,
    ["AssignmentData"] = {
        ["new"] = function(_, p_u_32, p_u_33) --[[ Name: new ]] --[[ Line: 58 ]]
            --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_29, (copy 3): v_u_6, (copy 4): v_u_1 ]]
            v_u_3:is_enum_member(p_u_32, v_u_29)
            v_u_3:is_true(v_u_6:singleton():contains_key(p_u_33))
            local v34 = {}
            v34.get_assignment_type = function(_) --[[ Name: get_assignment_type ]] --[[ Line: 64 ]]
                --[[ Upvalues: (ref 1): p_u_32 ]]
                return p_u_32;
            end;
            v34.set_assignment_type = function(_, p35) --[[ Name: set_assignment_type ]] --[[ Line: 65 ]]
                --[[ Upvalues: (ref 1): p_u_32 ]]
                p_u_32 = p35
            end;
            v34.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 67 ]]
                --[[ Upvalues: (ref 1): p_u_33 ]]
                return p_u_33;
            end;
            v34.set_song_key = function(_, p36) --[[ Name: set_song_key ]] --[[ Line: 68 ]]
                --[[ Upvalues: (ref 1): p_u_33 ]]
                p_u_33 = p36
            end;
            local v_u_37 = 0
            v34.get_end_time = function(_) --[[ Name: get_end_time ]] --[[ Line: 71 ]]
                --[[ Upvalues: (ref 1): v_u_37 ]]
                return v_u_37;
            end;
            v34.set_end_time = function(_, p38) --[[ Name: set_end_time ]] --[[ Line: 72 ]]
                --[[ Upvalues: (ref 1): v_u_37 ]]
                v_u_37 = p38
            end;
            local v_u_39 = v_u_1:new()
            v34.get_pet_owned_id_set = function(_) --[[ Name: get_pet_owned_id_set ]] --[[ Line: 75 ]]
                --[[ Upvalues: (copy 1): v_u_39 ]]
                return v_u_39;
            end;
            v34.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 77 ]]
                --[[ Upvalues: (ref 1): p_u_32, (ref 2): p_u_33, (ref 3): v_u_37, (copy 4): v_u_39 ]]
                return {
                    ["AssignmentType"] = p_u_32,
                    ["SongKey"] = p_u_33,
                    ["EndTime"] = v_u_37,
                    ["PetOwnedIDSet"] = v_u_39:key_list():get_table()
                };
            end;
            return v34;
        end
    },
    ["get_max_player_assignments"] = function(_) --[[ Name: get_max_player_assignments ]] --[[ Line: 107 ]]
        return 3;
    end,
    ["PlayerAssignmentData"] = {
        ["new"] = function(_) --[[ Name: new ]] --[[ Line: 112 ]]
            --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
            local v45 = {}
            local v_u_46 = v_u_2:new()
            v45.get_assignment_datas = function(_) --[[ Name: get_assignment_datas ]] --[[ Line: 117 ]]
                --[[ Upvalues: (copy 1): v_u_46 ]]
                return v_u_46;
            end;
            v45.get_used_song_key_set = function(_) --[[ Name: get_used_song_key_set ]] --[[ Line: 119 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_46 ]]
                local v47 = v_u_1:new()
                for _, v48 in v_u_46:key_itr() do
                    v47:add_set(v48:get_song_key())
                end;
                return v47;
            end;
            v45.get_used_pet_owned_id_set = function(_) --[[ Name: get_used_pet_owned_id_set ]] --[[ Line: 127 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_46 ]]
                local v49 = v_u_1:new()
                for _, v50 in v_u_46:key_itr() do
                    for _, v51 in v50:get_pet_owned_id_set():key_itr() do
                        v49:add_set(v51)
                    end;
                end;
                return v49;
            end;
            v45.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 137 ]]
                --[[ Upvalues: (copy 1): v_u_46 ]]
                local v52 = {
                    ["AssignmentDatas"] = {}
                }
                for _, v53 in v_u_46:key_itr() do
                    v52.AssignmentDatas[#v52.AssignmentDatas + 1] = v53:to_table()
                end;
                return v52;
            end;
            return v45;
        end
    },
    ["round_val"] = function(_, p26) --[[ Name: round_val ]] --[[ Line: 198 ]]
        local v27 = math.floor(p26)
        return math.max(0, v27 - v27 % 5);
    end
}
local v_u_29 = {
    ["Type1"] = 1,
    ["Type2"] = 2,
    ["Type3"] = 3
}
v_u_28.assignment_type_to_time_sec = function(_, p30) --[[ Name: assignment_type_to_time_sec ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_29 ]]
    return v_u_4.PetAssignmentDebugTimes == true and (p30 == v_u_29.Type1 and 5 or (p30 == v_u_29.Type2 and 15 or 30)) or (p30 == v_u_29.Type1 and 10800 or (p30 == v_u_29.Type2 and 21600 or 43200));
end;
v_u_28.assignment_type_to_string = function(_, p31) --[[ Name: assignment_type_to_string ]] --[[ Line: 45 ]]
    --[[ Upvalues: (copy 1): v_u_28 ]]
    return tostring(v_u_28:assignment_type_to_time_sec(p31) / 60 / 60) .. " hours";
end;
local v_u_40 = {
    ["new"] = function(_, p_u_32, p_u_33) --[[ Name: new ]] --[[ Line: 58 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_29, (copy 3): v_u_6, (copy 4): v_u_1 ]]
        v_u_3:is_enum_member(p_u_32, v_u_29)
        v_u_3:is_true(v_u_6:singleton():contains_key(p_u_33))
        local v34 = {}
        v34.get_assignment_type = function(_) --[[ Name: get_assignment_type ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): p_u_32 ]]
            return p_u_32;
        end;
        v34.set_assignment_type = function(_, p35) --[[ Name: set_assignment_type ]] --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): p_u_32 ]]
            p_u_32 = p35
        end;
        v34.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): p_u_33 ]]
            return p_u_33;
        end;
        v34.set_song_key = function(_, p36) --[[ Name: set_song_key ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): p_u_33 ]]
            p_u_33 = p36
        end;
        local v_u_37 = 0
        v34.get_end_time = function(_) --[[ Name: get_end_time ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37;
        end;
        v34.set_end_time = function(_, p38) --[[ Name: set_end_time ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            v_u_37 = p38
        end;
        local v_u_39 = v_u_1:new()
        v34.get_pet_owned_id_set = function(_) --[[ Name: get_pet_owned_id_set ]] --[[ Line: 75 ]]
            --[[ Upvalues: (copy 1): v_u_39 ]]
            return v_u_39;
        end;
        v34.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 77 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): p_u_33, (ref 3): v_u_37, (copy 4): v_u_39 ]]
            return {
                ["AssignmentType"] = p_u_32,
                ["SongKey"] = p_u_33,
                ["EndTime"] = v_u_37,
                ["PetOwnedIDSet"] = v_u_39:key_list():get_table()
            };
        end;
        return v34;
    end
}
local v_u_41 = v_u_40:new(v_u_29.Type1, 1)
v_u_40.get_default = function(_) --[[ Name: get_default ]] --[[ Line: 90 ]]
    --[[ Upvalues: (copy 1): v_u_41 ]]
    return v_u_41;
end;
v_u_40.from_table = function(_, p42) --[[ Name: from_table ]] --[[ Line: 92 ]]
    --[[ Upvalues: (copy 1): v_u_40, (copy 2): v_u_3, (copy 3): v_u_28 ]]
    local v43 = v_u_40:new(p42.AssignmentType, p42.SongKey)
    v43:set_end_time(p42.EndTime)
    v_u_3:is_true(#p42.PetOwnedIDSet > 0)
    v_u_3:is_true(#p42.PetOwnedIDSet <= v_u_28:get_max_pets_in_assignment())
    for _, v44 in pairs(p42.PetOwnedIDSet) do
        v_u_3:is_int(v44)
        v43:get_pet_owned_id_set():add_set(v44)
    end;
    return v43;
end;
local v_u_54 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 112 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v45 = {}
        local v_u_46 = v_u_2:new()
        v45.get_assignment_datas = function(_) --[[ Name: get_assignment_datas ]] --[[ Line: 117 ]]
            --[[ Upvalues: (copy 1): v_u_46 ]]
            return v_u_46;
        end;
        v45.get_used_song_key_set = function(_) --[[ Name: get_used_song_key_set ]] --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_46 ]]
            local v47 = v_u_1:new()
            for _, v48 in v_u_46:key_itr() do
                v47:add_set(v48:get_song_key())
            end;
            return v47;
        end;
        v45.get_used_pet_owned_id_set = function(_) --[[ Name: get_used_pet_owned_id_set ]] --[[ Line: 127 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_46 ]]
            local v49 = v_u_1:new()
            for _, v50 in v_u_46:key_itr() do
                for _, v51 in v50:get_pet_owned_id_set():key_itr() do
                    v49:add_set(v51)
                end;
            end;
            return v49;
        end;
        v45.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 137 ]]
            --[[ Upvalues: (copy 1): v_u_46 ]]
            local v52 = {
                ["AssignmentDatas"] = {}
            }
            for _, v53 in v_u_46:key_itr() do
                v52.AssignmentDatas[#v52.AssignmentDatas + 1] = v53:to_table()
            end;
            return v52;
        end;
        return v45;
    end
}
v_u_54.from_table = function(_, p55) --[[ Name: from_table ]] --[[ Line: 149 ]]
    --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_40 ]]
    local v56 = v_u_54:new()
    for _, v57 in pairs(p55.AssignmentDatas) do
        v56:get_assignment_datas():push_back(v_u_40:from_table(v57))
    end;
    return v56;
end;
local v_u_58 = v7:new(0, 1250)
v_u_28.get_gear_power_calc_range = function(_) --[[ Name: get_gear_power_calc_range ]] --[[ Line: 159 ]]
    --[[ Upvalues: (copy 1): v_u_58 ]]
    return v_u_58;
end;
local v_u_59 = v_u_1:new({
    [v_u_29.Type1] = v7:new(150, 500),
    [v_u_29.Type2] = v7:new(400, 2000),
    [v_u_29.Type3] = v7:new(1000, 5000)
})
local v_u_60 = v_u_1:new({
    [v_u_29.Type1] = v7:new(50, 100),
    [v_u_29.Type2] = v7:new(85, 175),
    [v_u_29.Type3] = v7:new(150, 300)
})
local v_u_61 = v_u_1:new({
    [v_u_29.Type1] = v7:new(25, 50),
    [v_u_29.Type2] = v7:new(50, 100),
    [v_u_29.Type3] = v7:new(100, 200)
})
local function f_get_calculated_value_for_assignment_type_gear_power_and_assignment_type_to_value_dict(p62, p63, p64) --[[ Name: get_calculated_value_for_assignment_type_gear_power_and_assignment_type_to_value_dict ]] --[[ Line: 181 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_29, (copy 3): v_u_5, (copy 4): v_u_58, (copy 5): v_u_8 ]]
    v_u_3:is_enum_member(p62, v_u_29)
    v_u_3:is_number(p63)
    local v65 = v_u_5:clamp(p63, v_u_58:min(), v_u_58:max())
    local v66 = p64:get(p62)
    v_u_3:is_non_nil(v66)
    return v_u_8:Lerp(v66:min(), v66:max(), v65 / v_u_58:max());
end;
local function _(p67) --[[ Name: round_val ]] --[[ Line: 193 ]]
    local v68 = math.floor(p67)
    return math.max(0, v68 - v68 % 5);
end;
v_u_28.get_exp_gain_for_assignment_type_and_gear_power = function(_, p69, p70) --[[ Name: get_exp_gain_for_assignment_type_and_gear_power ]] --[[ Line: 200 ]]
    --[[ Upvalues: (copy 1): f_get_calculated_value_for_assignment_type_gear_power_and_assignment_type_to_value_dict, (copy 2): v_u_59 ]]
    local v71 = math.floor((f_get_calculated_value_for_assignment_type_gear_power_and_assignment_type_to_value_dict(p69, p70, v_u_59)))
    return math.max(0, v71 - v71 % 5);
end;
v_u_28.get_event_point_gain_for_assignment_type_and_gear_power = function(_, p72, p73) --[[ Name: get_event_point_gain_for_assignment_type_and_gear_power ]] --[[ Line: 206 ]]
    --[[ Upvalues: (copy 1): f_get_calculated_value_for_assignment_type_gear_power_and_assignment_type_to_value_dict, (copy 2): v_u_60 ]]
    local v74 = math.floor((f_get_calculated_value_for_assignment_type_gear_power_and_assignment_type_to_value_dict(p72, p73, v_u_60)))
    return math.max(0, v74 - v74 % 5);
end;
v_u_28.get_team_contribution_point_gain_for_assignment_type_and_gear_power = function(_, p75, p76) --[[ Name: get_team_contribution_point_gain_for_assignment_type_and_gear_power ]] --[[ Line: 212 ]]
    --[[ Upvalues: (copy 1): f_get_calculated_value_for_assignment_type_gear_power_and_assignment_type_to_value_dict, (copy 2): v_u_61 ]]
    local v77 = math.floor((f_get_calculated_value_for_assignment_type_gear_power_and_assignment_type_to_value_dict(p75, p76, v_u_61)))
    return math.max(0, v77 - v77 % 5);
end;
return v_u_28;
