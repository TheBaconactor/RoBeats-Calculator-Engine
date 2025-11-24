-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:13 PM
-- Cached decompilation

require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.ForwardCompatSerialization)
local v_u_12 = {
    ["get_min_assigned_difficulty"] = function(_) --[[ Name: get_min_assigned_difficulty ]] --[[ Line: 123 ]]
        return 1;
    end,
    ["get_max_assigned_difficulty"] = function(_) --[[ Name: get_max_assigned_difficulty ]] --[[ Line: 124 ]]
        return 50;
    end,
    ["get_assigned_difficulty_range"] = function(_) --[[ Name: get_assigned_difficulty_range ]] --[[ Line: 125 ]]
        return 5;
    end,
    ["get_map_name_max_length"] = function(_) --[[ Name: get_map_name_max_length ]] --[[ Line: 140 ]]
        return 255;
    end,
    ["get_max_recent_saved_map_info_count"] = function(_) --[[ Name: get_max_recent_saved_map_info_count ]] --[[ Line: 141 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4 ]]
        return v_u_5.TestLowerSavedMapInfoCount == true and v_u_4:is_dev_build() and 3 or 500;
    end,
    ["get_default_custom_map_key"] = function(_) --[[ Name: get_default_custom_map_key ]] --[[ Line: 147 ]]
        return "";
    end,
    ["info_list_to_table"] = function(_, p7) --[[ Name: info_list_to_table ]] --[[ Line: 175 ]]
        local v8 = {}
        for v9 = 1, p7:count() do
            v8[v9] = p7:get(v9):to_table()
        end;
        return v8;
    end,
    ["write_editable_saved_map_info_from_src_to_dest"] = function(_, p10, p11) --[[ Name: write_editable_saved_map_info_from_src_to_dest ]] --[[ Line: 201 ]]
        p11:set_like_count(p10:get_like_count())
        p11:set_comment_count(p10:get_comment_count())
    end
}
v_u_12.new = function(_) --[[ Name: new ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_12, (copy 4): v_u_6 ]]
    local v13 = {}
    local v_u_14 = v_u_3:invalid_songkey()
    v13.get_source_songkey = function(_) --[[ Name: get_source_songkey ]] --[[ Line: 18 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        return v_u_14;
    end;
    v13.set_source_songkey = function(_, p15) --[[ Name: set_source_songkey ]] --[[ Line: 19 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_14, (ref 3): v_u_3 ]]
        v_u_2:is_int(p15)
        local v16 = v_u_2
        local v17
        if v_u_14 == v_u_3:invalid_songkey() then
            v17 = true
        elseif v_u_14 >= 1 then
            v17 = v_u_14 <= v_u_3:singleton():count() + 64
        else
            v17 = false
        end;
        v16:is_true(v17)
        v_u_14 = p15
    end;
    local v_u_18 = 0
    v13.get_last_edit_time = function(_) --[[ Name: get_last_edit_time ]] --[[ Line: 28 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        return v_u_18;
    end;
    v13.set_last_edit_time = function(_, p19) --[[ Name: set_last_edit_time ]] --[[ Line: 29 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_18 ]]
        v_u_2:is_number(p19)
        v_u_18 = p19
    end;
    local v_u_20 = ""
    v13.get_custom_map_name = function(_) --[[ Name: get_custom_map_name ]] --[[ Line: 35 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20;
    end;
    v13.set_custom_map_name = function(_, p21) --[[ Name: set_custom_map_name ]] --[[ Line: 36 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_20 ]]
        v_u_2:is_string(p21)
        v_u_20 = p21
    end;
    v13.get_default_custom_map_name = function(p22) --[[ Name: get_default_custom_map_name ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_3 ]]
        return string.format("New Map: %s", v_u_3:singleton():get_title_for_key(p22:get_source_songkey()));
    end;
    local v_u_23 = ""
    v13.get_creator_name = function(_) --[[ Name: get_creator_name ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        return v_u_23;
    end;
    v13.set_creator_name = function(_, p24) --[[ Name: set_creator_name ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_23 ]]
        v_u_2:is_string(p24)
        v_u_23 = p24
    end;
    local v_u_25 = 0
    v13.get_creator_rbxid = function(_) --[[ Name: get_creator_rbxid ]] --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25;
    end;
    v13.set_creator_rbxid = function(_, p26) --[[ Name: set_creator_rbxid ]] --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_25 ]]
        v_u_2:is_int(p26)
        v_u_25 = p26
    end;
    local v_u_27 = v_u_12:get_default_custom_map_key()
    v13.get_custom_map_data_key = function(_) --[[ Name: get_custom_map_data_key ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    v13.set_custom_map_data_key = function(_, p28) --[[ Name: set_custom_map_data_key ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_27 ]]
        v_u_2:is_string(p28)
        v_u_27 = p28
    end;
    local v_u_29 = 0
    v13.get_like_count = function(_) --[[ Name: get_like_count ]] --[[ Line: 72 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    v13.set_like_count = function(_, p30) --[[ Name: set_like_count ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_29 ]]
        v_u_2:is_int(p30)
        v_u_29 = p30
    end;
    local v_u_31 = 0
    v13.get_comment_count = function(_) --[[ Name: get_comment_count ]] --[[ Line: 79 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31;
    end;
    v13.set_comment_count = function(_, p32) --[[ Name: set_comment_count ]] --[[ Line: 80 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_31 ]]
        v_u_2:is_int(p32)
        v_u_31 = p32
    end;
    local v_u_33 = 0
    v13.has_assigned_difficulty = function(_) --[[ Name: has_assigned_difficulty ]] --[[ Line: 86 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33 ~= 0;
    end;
    v13.get_assigned_difficulty_string = function(p34) --[[ Name: get_assigned_difficulty_string ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return not p34:has_assigned_difficulty() and "-" or tostring(v_u_33);
    end;
    v13.get_assigned_difficulty = function(_) --[[ Name: get_assigned_difficulty ]] --[[ Line: 96 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33;
    end;
    v13.set_assigned_difficulty = function(_, p35) --[[ Name: set_assigned_difficulty ]] --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_12, (ref 3): v_u_33 ]]
        v_u_2:is_int(p35)
        local v36 = v_u_2
        local v37
        if p35 >= 0 then
            v37 = p35 <= v_u_12:get_max_assigned_difficulty()
        else
            v37 = false
        end;
        v36:is_true(v37)
        v_u_33 = p35
    end;
    local v_u_38 = v_u_6:new()
    v13.get_forward_compat_serialization = function(_) --[[ Name: get_forward_compat_serialization ]] --[[ Line: 104 ]]
        --[[ Upvalues: (copy 1): v_u_38 ]]
        return v_u_38;
    end;
    v13.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 106 ]]
        --[[ Upvalues: (copy 1): v_u_38, (ref 2): v_u_14, (ref 3): v_u_18, (ref 4): v_u_20, (ref 5): v_u_23, (ref 6): v_u_25, (ref 7): v_u_27, (ref 8): v_u_29, (ref 9): v_u_31, (ref 10): v_u_33 ]]
        return v_u_38:write_forward_compat_properties_to_table({
            ["SourceSongKey"] = v_u_14,
            ["LastEditTime"] = v_u_18,
            ["CustomMapName"] = v_u_20,
            ["CreatorName"] = v_u_23,
            ["CreatorRbxID"] = v_u_25,
            ["CustomMapDataKey"] = v_u_27,
            ["LikeCount"] = v_u_29,
            ["CommentCount"] = v_u_31,
            ["AssignedDifficulty"] = v_u_33
        });
    end;
    return v13;
end;
v_u_12.calc_difficulty_get_min_max_assigned_difficulty = function(_, p39) --[[ Name: calc_difficulty_get_min_max_assigned_difficulty ]] --[[ Line: 126 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_12 ]]
    return v_u_4:clamp(p39 - v_u_12:get_assigned_difficulty_range(), v_u_12:get_min_assigned_difficulty(), v_u_12:get_max_assigned_difficulty()), v_u_4:clamp(p39 + v_u_12:get_assigned_difficulty_range(), v_u_12:get_min_assigned_difficulty(), v_u_12:get_max_assigned_difficulty());
end;
v_u_12.from_table = function(_, p40) --[[ Name: from_table ]] --[[ Line: 149 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    local v41 = v_u_12:new()
    v41:set_source_songkey(p40.SourceSongKey)
    v41:set_last_edit_time(p40.LastEditTime)
    v41:set_custom_map_name(p40.CustomMapName)
    v41:set_creator_name(p40.CreatorName)
    v41:set_creator_rbxid(p40.CreatorRbxID)
    v41:set_custom_map_data_key(p40.CustomMapDataKey)
    if p40.LikeCount ~= nil then
        v41:set_like_count(p40.LikeCount)
    end;
    if p40.CommentCount ~= nil then
        v41:set_comment_count(p40.CommentCount)
    end;
    if p40.AssignedDifficulty ~= nil then
        v41:set_assigned_difficulty(p40.AssignedDifficulty)
    end;
    return v41;
end;
v_u_12.from_datastore_forward_compat_table = function(_, p42) --[[ Name: from_datastore_forward_compat_table ]] --[[ Line: 169 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    local v43 = v_u_12:from_table(p42)
    v43:get_forward_compat_serialization():store_forward_compat_properties(v43:to_table(), p42)
    return v43;
end;
v_u_12.info_list_from_table = function(_, p44) --[[ Name: info_list_from_table ]] --[[ Line: 183 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_12 ]]
    local v45 = v_u_1:new()
    for v46 = 1, #p44 do
        v45:push_back((v_u_12:from_table(p44[v46])))
    end;
    return v45;
end;
v_u_12.info_list_from_datastore_forward_compat_table = function(_, p47) --[[ Name: info_list_from_datastore_forward_compat_table ]] --[[ Line: 192 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_12 ]]
    local v48 = v_u_1:new()
    for v49 = 1, #p47 do
        v48:push_back((v_u_12:from_datastore_forward_compat_table(p47[v49])))
    end;
    return v48;
end;
return v_u_12;
