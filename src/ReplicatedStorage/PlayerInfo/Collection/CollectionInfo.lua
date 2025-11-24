-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v2 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.Collection.OwnedIdSet)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPUtil)
local s_HttpService_0 = game:GetService("HttpService")
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_9 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_10 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_11 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_13 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
local v_u_16 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v17 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_18 = nil
local v_u_19 = nil
local v_u_20 = nil
local v_u_21 = nil
local v_u_22 = nil
v17:require_shared(function() --[[ Line: 26 ]]
    --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_19, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_22 ]]
    v_u_18 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
    v_u_19 = require(game.ReplicatedStorage.Pets.PetUtils)
    v_u_20 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
    v_u_21 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
    v_u_22 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
end)
local v_u_23 = {
    ["Type"] = {
        ["Dances"] = 1,
        ["Gear"] = 2,
        ["Minis"] = 3,
        ["Stages"] = 4,
        ["Icons"] = 5,
        ["Songs"] = 6
    }
}
local v_u_24 = v_u_4:new()
local v_u_25 = v_u_19
local v_u_26 = v_u_20
local v_u_27 = v_u_18
local v_u_28 = v_u_21
for _, v29 in pairs(v_u_23.Type) do
    v_u_24:add_set(v29)
end;
v_u_23.get_all_collection_types_set = function(_) --[[ Name: get_all_collection_types_set ]] --[[ Line: 49 ]]
    --[[ Upvalues: (copy 1): v_u_24 ]]
    return v_u_24;
end;
v_u_23.get_collection_types_display_order_list = function(_) --[[ Name: get_collection_types_display_order_list ]] --[[ Line: 50 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_23 ]]
    return v_u_3:new({
        v_u_23.Type.Songs,
        v_u_23.Type.Dances,
        v_u_23.Type.Gear,
        v_u_23.Type.Icons,
        v_u_23.Type.Minis,
        v_u_23.Type.Stages
    });
end;
v_u_23.type_to_name = function(_, p30, p31) --[[ Name: type_to_name ]] --[[ Line: 61 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    local v32 = true
    local v33
    if p30 == v_u_23.Type.Dances then
        v33 = "Dance"
    elseif p30 == v_u_23.Type.Gear then
        v32 = false
        v33 = "Gear"
    elseif p30 == v_u_23.Type.Minis then
        v33 = "Mini"
    elseif p30 == v_u_23.Type.Stages then
        v33 = "Stage"
    elseif p30 == v_u_23.Type.Icons then
        v33 = "Icon"
    elseif p30 == v_u_23.Type.Songs then
        v33 = "Song"
    else
        v33 = "?"
    end;
    if v32 and (p31 == nil or typeof(p31) == "number" and p31 > 1) then
        v33 = v33 .. "s"
    end;
    return v33;
end;
v_u_23.type_to_icon = function(_, p34) --[[ Name: type_to_icon ]] --[[ Line: 88 ]]
    --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_25, (copy 3): v_u_7 ]]
    if p34 == v_u_23.Type.Dances then
        return "rbxassetid://2993241780";
    elseif p34 == v_u_23.Type.Gear then
        return "rbxassetid://1520246011";
    elseif p34 == v_u_23.Type.Minis then
        return v_u_25:get_pet_icon();
    elseif p34 == v_u_23.Type.Stages then
        return "rbxassetid://11111386659";
    elseif p34 == v_u_23.Type.Icons then
        return "rbxassetid://11111386743";
    elseif p34 == v_u_23.Type.Songs then
        return v_u_7:get_iconhd_song();
    else
        return v_u_7:get_question_assetid();
    end;
end;
v_u_23.does_collection_type_require_playerblob_update = function(_, p35) --[[ Name: does_collection_type_require_playerblob_update ]] --[[ Line: 107 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    return p35 == v_u_23.Type.Stages and true or (p35 == v_u_23.Type.Icons and true or p35 == v_u_23.Type.Songs);
end;
v_u_23.new = function(_) --[[ Name: new ]] --[[ Line: 120 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_23, (copy 3): v_u_6, (copy 4): v_u_5, (copy 5): v_u_1, (copy 6): v_u_3, (copy 7): s_HttpService_0 ]]
    local v_u_36 = {}
    local v_u_37 = v_u_4:new()
    local v_u_38 = v_u_4:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 126 ]]
        --[[ Upvalues: (ref 1): v_u_23, (copy 2): v_u_36, (ref 3): v_u_6 ]]
        for v39, _ in v_u_23:get_all_collection_types_set():key_itr() do
            v_u_36:add_collection_type_owned_id_set(v39, v_u_6:new())
        end;
    end;
    v_u_36.add_collection_type_owned_id_set = function(_, p40, p41) --[[ Name: add_collection_type_owned_id_set ]] --[[ Line: 132 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_23, (ref 3): v_u_1, (copy 4): v_u_37 ]]
        v_u_5:is_non_nil(p41.set_id_owned)
        if not v_u_5:test_enum_member(p40, v_u_23.Type) then
            return v_u_1:warnf("CollectionInfo:add_collection_type_owned_id_set invalid collection_type(%s)", (tostring(p40)));
        end;
        v_u_37:add(p40, p41)
    end;
    v_u_36.add_unhandled_type_owned_id_set = function(_, p42, p43) --[[ Name: add_unhandled_type_owned_id_set ]] --[[ Line: 138 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_23, (copy 3): v_u_38 ]]
        v_u_5:is_non_nil(p43.set_id_owned)
        v_u_5:is_false(v_u_5:test_enum_member(p42, v_u_23.Type))
        v_u_38:add(p42, p43)
    end;
    v_u_36.get_collection_type_owned_count = function(_, p44) --[[ Name: get_collection_type_owned_count ]] --[[ Line: 144 ]]
        --[[ Upvalues: (copy 1): v_u_37 ]]
        return not v_u_37:contains(p44) and 0 or v_u_37:get(p44):get_count();
    end;
    v_u_36.set_collection_type_and_id_owned = function(_, p45, p46, p47) --[[ Name: set_collection_type_and_id_owned ]] --[[ Line: 152 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_23, (ref 3): v_u_1, (copy 4): v_u_37 ]]
        if not v_u_5:test_enum_member(p45, v_u_23.Type) then
            return v_u_1:warnf("CollectionInfo:set_collection_type_and_id_owned invalid collection_type(%s)", (tostring(p45)));
        end;
        v_u_37:get(p45):set_id_owned(p46, p47)
    end;
    v_u_36.get_collection_type_owned_entry_list = function(_, p48) --[[ Name: get_collection_type_owned_entry_list ]] --[[ Line: 157 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_37, (ref 3): v_u_23 ]]
        local v49 = v_u_3:new()
        if v_u_37:contains(p48) ~= true then
            return v49;
        end;
        for _, v50 in v_u_37:get(p48):get_owned_id_list():key_itr() do
            local v51 = v_u_23:get_entry_for_collection_type_and_collection_id(p48, v50)
            if v51 then
                v49:push_back(v51)
            end;
        end;
        return v49;
    end;
    v_u_36.get_collection_type_and_id_owned = function(_, p52, p53) --[[ Name: get_collection_type_and_id_owned ]] --[[ Line: 169 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_23, (ref 3): v_u_1, (copy 4): v_u_37 ]]
        if v_u_5:test_enum_member(p52, v_u_23.Type) then
            return v_u_37:get(p52):is_id_owned(p53);
        end;
        v_u_1:warnf("CollectionInfo:get_collection_type_and_id_owned invalid collection_type(%s)", (tostring(p52)))
        return false;
    end;
    v_u_36.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 174 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_37, (copy 3): v_u_38, (ref 4): v_u_6 ]]
        local v54 = v_u_3:new()
        local v55 = 1
        for v56, _ in v_u_37:key_itr() do
            v55 = math.max(v55, v56)
        end;
        for v57, _ in v_u_38:key_itr() do
            v55 = math.max(v55, v57)
        end;
        for _ = 1, v55 do
            v54:push_back(v_u_6:new():to_table())
        end;
        for v58, v59 in v_u_37:key_itr() do
            v54:set(v58, v59:to_table())
        end;
        for v60, v61 in v_u_38:key_itr() do
            v54:set(v60, v61:to_table())
        end;
        return v54:get_table();
    end;
    v_u_36.to_json = function(p62) --[[ Name: to_json ]] --[[ Line: 199 ]]
        --[[ Upvalues: (ref 1): s_HttpService_0 ]]
        return s_HttpService_0:JSONEncode(p62:to_table());
    end;
    f_cons()
    return v_u_36;
end;
v_u_23.from_table = function(_, p63) --[[ Name: from_table ]] --[[ Line: 207 ]]
    --[[ Upvalues: (copy 1): v_u_23, (copy 2): v_u_6, (copy 3): v_u_5 ]]
    local v64 = v_u_23:new()
    for v65, v66 in pairs(p63) do
        local v67 = v_u_6:from_table(v66)
        if v_u_5:test_enum_member(v65, v_u_23.Type) then
            v64:add_collection_type_owned_id_set(v65, v67)
        else
            v64:add_unhandled_type_owned_id_set(v65, v67)
        end;
    end;
    return v64;
end;
v_u_23.from_json = function(_, p_u_68) --[[ Name: from_json ]] --[[ Line: 220 ]]
    --[[ Upvalues: (copy 1): s_HttpService_0, (copy 2): v_u_1, (copy 3): v_u_23 ]]
    local v_u_69 = {}
    if typeof(p_u_68) == "string" and #p_u_68 > 0 then
        local v70, v71 = pcall(function() --[[ Line: 224 ]]
            --[[ Upvalues: (ref 1): v_u_69, (ref 2): s_HttpService_0, (copy 3): p_u_68 ]]
            v_u_69 = s_HttpService_0:JSONDecode(p_u_68)
        end)
        if not v70 then
            v_u_1:warnf("CollectionInfo:from_json failed[%s](%s)", v71, (tostring(p_u_68)))
        end;
    end;
    return v_u_23:from_table(v_u_69);
end;
local v_u_72 = v2:new()
v_u_23.Entry = {}
v_u_23.Entry.new = function(_, p_u_73, p_u_74, p_u_75, p_u_76) --[[ Name: new ]] --[[ Line: 238 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_23, (copy 3): v_u_8, (copy 4): v_u_9, (copy 5): v_u_10, (copy 6): v_u_11, (copy 7): v_u_12, (copy 8): v_u_13, (copy 9): v_u_7, (ref 10): v_u_28, (ref 11): v_u_26, (ref 12): v_u_25, (ref 13): v_u_27, (copy 14): v_u_14, (copy 15): v_u_15, (copy 16): v_u_16 ]]
    v_u_5:is_enum_member(p_u_73, v_u_23.Type)
    v_u_5:is_int_greater_than(p_u_74, 1)
    v_u_5:is_int(p_u_75)
    v_u_5:is_true(p_u_75 == -1 and true or p_u_75 > 0)
    v_u_5:is_int_greater_than(p_u_76, 1)
    local v77 = {}
    v77.get_collection_type = function(_) --[[ Name: get_collection_type ]] --[[ Line: 247 ]]
        --[[ Upvalues: (copy 1): p_u_73 ]]
        return p_u_73;
    end;
    v77.get_collection_id = function(_) --[[ Name: get_collection_id ]] --[[ Line: 248 ]]
        --[[ Upvalues: (copy 1): p_u_74 ]]
        return p_u_74;
    end;
    v77.get_database_id = function(_) --[[ Name: get_database_id ]] --[[ Line: 249 ]]
        --[[ Upvalues: (copy 1): p_u_76 ]]
        return p_u_76;
    end;
    v77.get_display_collection_id = function(_) --[[ Name: get_display_collection_id ]] --[[ Line: 250 ]]
        --[[ Upvalues: (copy 1): p_u_75 ]]
        return p_u_75;
    end;
    v77.should_display_entry = function(_) --[[ Name: should_display_entry ]] --[[ Line: 251 ]]
        --[[ Upvalues: (copy 1): p_u_75 ]]
        return p_u_75 ~= -1;
    end;
    v77.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 253 ]]
        --[[ Upvalues: (copy 1): p_u_73, (ref 2): v_u_23, (ref 3): v_u_8, (copy 4): p_u_76, (ref 5): v_u_9, (ref 6): v_u_10, (ref 7): v_u_11, (ref 8): v_u_12, (ref 9): v_u_13 ]]
        if p_u_73 == v_u_23.Type.Dances then
            return v_u_8:singleton():get_dance_name_for_id(p_u_76);
        elseif p_u_73 == v_u_23.Type.Gear then
            return v_u_9:singleton():get_equipment_for_id(p_u_76):get_name();
        elseif p_u_73 == v_u_23.Type.Minis then
            return v_u_10:singleton():get_name_for_petid(p_u_76);
        elseif p_u_73 == v_u_23.Type.Stages then
            return v_u_11:singleton():get_stage_info_for_id(p_u_76):get_name();
        elseif p_u_73 == v_u_23.Type.Icons then
            return v_u_12:singleton():get_fevericon_for_id(p_u_76):get_name();
        else
            return p_u_73 ~= v_u_23.Type.Songs and "?" or v_u_13:singleton():get_title_for_key(p_u_76);
        end;
    end;
    v77.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 271 ]]
        --[[ Upvalues: (copy 1): p_u_73, (ref 2): v_u_23, (ref 3): v_u_8, (copy 4): p_u_76, (ref 5): v_u_9, (ref 6): v_u_10, (ref 7): v_u_11, (ref 8): v_u_12, (ref 9): v_u_13, (ref 10): v_u_7 ]]
        if p_u_73 == v_u_23.Type.Dances then
            return v_u_8:singleton():get_dance_icon_for_id(p_u_76);
        elseif p_u_73 == v_u_23.Type.Gear then
            return v_u_9:singleton():get_equipment_for_id(p_u_76):get_icon();
        elseif p_u_73 == v_u_23.Type.Minis then
            return v_u_10:singleton():get_data_for_petid(p_u_76):get_icon();
        elseif p_u_73 == v_u_23.Type.Stages then
            return v_u_11:singleton():get_stage_info_for_id(p_u_76):get_icon();
        elseif p_u_73 == v_u_23.Type.Icons then
            return v_u_12:singleton():get_fevericon_for_id(p_u_76):get_icon();
        elseif p_u_73 == v_u_23.Type.Songs then
            return v_u_13:singleton():get_coverimage_assetid_for_key(p_u_76);
        else
            return v_u_7:get_question_assetid();
        end;
    end;
    v77.does_playerblob_own_entry = function(_, p78) --[[ Name: does_playerblob_own_entry ]] --[[ Line: 289 ]]
        --[[ Upvalues: (copy 1): p_u_73, (ref 2): v_u_23, (ref 3): v_u_28, (copy 4): p_u_76, (ref 5): v_u_26, (ref 6): v_u_25, (ref 7): v_u_11, (ref 8): v_u_27, (ref 9): v_u_12, (ref 10): v_u_14 ]]
        if p_u_73 == v_u_23.Type.Dances then
            return v_u_28:get_owned_danceid_to_equipped_dict(p78):contains(p_u_76);
        elseif p_u_73 == v_u_23.Type.Gear then
            return v_u_26:playerblob_get_owned_count_of_equipmentid(p78, p_u_76) > 0;
        elseif p_u_73 == v_u_23.Type.Minis then
            return v_u_25:playerblob_get_owned_petid_set(p78):contains(p_u_76);
        elseif p_u_73 == v_u_23.Type.Stages then
            return v_u_27:get_count_of_material(p78, (v_u_11:singleton():get_stage_info_for_id(p_u_76):get_material_id())) > 0;
        elseif p_u_73 == v_u_23.Type.Icons then
            return v_u_27:get_count_of_material(p78, (v_u_12:singleton():get_fevericon_for_id(p_u_76):get_material_id())) > 0;
        elseif p_u_73 == v_u_23.Type.Songs then
            return v_u_14:get_song_key_owned_count(p78, p_u_76) > 0;
        else
            return false;
        end;
    end;
    v77.does_entry_type_require_playerblob_update = function(_) --[[ Name: does_entry_type_require_playerblob_update ]] --[[ Line: 309 ]]
        --[[ Upvalues: (ref 1): v_u_23, (copy 2): p_u_73 ]]
        return v_u_23:does_collection_type_require_playerblob_update(p_u_73);
    end;
    v77.try_register_entry_to_playerblob = function(p79, p80) --[[ Name: try_register_entry_to_playerblob ]] --[[ Line: 313 ]]
        --[[ Upvalues: (copy 1): p_u_73, (ref 2): v_u_23, (ref 3): v_u_11, (copy 4): p_u_76, (ref 5): v_u_27, (ref 6): v_u_12, (ref 7): v_u_14 ]]
        if p79:does_playerblob_own_entry(p80) ~= true then
            return false;
        end;
        if p79:does_entry_type_require_playerblob_update() == false then
            return true;
        end;
        if p_u_73 == v_u_23.Type.Stages then
            v_u_27:add_crafting_materials_of_id(p80, v_u_11:singleton():get_stage_info_for_id(p_u_76):get_material_id(), -1)
            return true;
        end;
        if p_u_73 == v_u_23.Type.Icons then
            v_u_27:add_crafting_materials_of_id(p80, v_u_12:singleton():get_fevericon_for_id(p_u_76):get_material_id(), -1)
            return true;
        end;
        if p_u_73 ~= v_u_23.Type.Songs then
            return false;
        end;
        v_u_14:remove_songs(p80, p_u_76, 1)
        return true;
    end;
    v77.get_collection_point_amount = function(_) --[[ Name: get_collection_point_amount ]] --[[ Line: 333 ]]
        --[[ Upvalues: (copy 1): p_u_73, (ref 2): v_u_23, (ref 3): v_u_8, (copy 4): p_u_76, (ref 5): v_u_15, (ref 6): v_u_9, (ref 7): v_u_10, (ref 8): v_u_16, (ref 9): v_u_13 ]]
        if p_u_73 == v_u_23.Type.Dances then
            local v81 = v_u_8:singleton():get_dance_rarity_for_id(p_u_76)
            return v81 == v_u_15.Epic and 5 or (v81 == v_u_15.Rare and 3 or 1);
        end;
        if p_u_73 == v_u_23.Type.Gear then
            local v82 = v_u_9:singleton():get_equipment_for_id(p_u_76)
            return v82 == 3 and 10 or (v82 == 2 and 4 or 2);
        end;
        if p_u_73 == v_u_23.Type.Minis then
            return v_u_10:singleton():get_data_for_petid(p_u_76) == v_u_16.Rarity.Tier2 and 5 or 3;
        end;
        if p_u_73 == v_u_23.Type.Stages then
            return 5;
        end;
        if p_u_73 == v_u_23.Type.Icons then
            return 20;
        end;
        if p_u_73 ~= v_u_23.Type.Songs then
            return 0;
        end;
        local v83 = v_u_13:singleton():key_get_audiomod(p_u_76)
        return v_u_13:singleton():key_is_remix_flagged(p_u_76) and 0 or (v_u_13:singleton():key_is_vip(p_u_76) and (v83 == v_u_13.MOD_HARDMODE and 10 or 5) or (v83 == v_u_13.MOD_HARDMODE and 2 or 1));
    end;
    return v77;
end;
v_u_23.get_collection_type_to_entries = function(_) --[[ Name: get_collection_type_to_entries ]] --[[ Line: 403 ]]
    --[[ Upvalues: (copy 1): v_u_72 ]]
    return v_u_72;
end;
v_u_23.collection_type_get_entries_list = function(_, p84) --[[ Name: collection_type_get_entries_list ]] --[[ Line: 405 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_23, (copy 3): v_u_72 ]]
    v_u_5:is_enum_member(p84, v_u_23.Type)
    return v_u_72:list_of(p84);
end;
v_u_23.get_collection_info_from_playerblob = function(_, p85) --[[ Name: get_collection_info_from_playerblob ]] --[[ Line: 410 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    return v_u_23:from_json(p85.CollectionInfoJson);
end;
v_u_23.get_playerblob_collection_type_collection_info_unregistered_owned_entries_list = function(_, p86, p87, p88) --[[ Name: get_playerblob_collection_type_collection_info_unregistered_owned_entries_list ]] --[[ Line: 414 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_23 ]]
    local v89 = v_u_3:new()
    for _, v90 in v_u_23:collection_type_get_entries_list(p87):key_itr() do
        if v90:should_display_entry() == true and (p88:get_collection_type_and_id_owned(v90:get_collection_type(), v90:get_collection_id()) == false and v90:does_playerblob_own_entry(p86) == true) then
            v89:push_back(v90)
        end;
    end;
    return v89;
end;
local v_u_91 = v_u_4:new()
local function f___collection_type_and_collection_id_to_entry_cache_key(p92, p93) --[[ Name: __collection_type_and_collection_id_to_entry_cache_key ]] --[[ Line: 426 ]]
    return string.format("%d_%d", p92, p93);
end;
v_u_23.get_entry_for_collection_type_and_collection_id = function(_, p94, p95) --[[ Name: get_entry_for_collection_type_and_collection_id ]] --[[ Line: 427 ]]
    --[[ Upvalues: (copy 1): v_u_91, (copy 2): f___collection_type_and_collection_id_to_entry_cache_key ]]
    return v_u_91:get(f___collection_type_and_collection_id_to_entry_cache_key(p94, p95));
end;
local v_u_96 = v_u_4:new()
local function f___collection_type_and_database_id_to_entry_cache_cache_key(p97, p98) --[[ Name: __collection_type_and_database_id_to_entry_cache_cache_key ]] --[[ Line: 434 ]]
    return string.format("%d_%d", p97, p98);
end;
v_u_23.get_entry_for_collection_type_and_database_id = function(_, p99, p100) --[[ Name: get_entry_for_collection_type_and_database_id ]] --[[ Line: 435 ]]
    --[[ Upvalues: (copy 1): v_u_96, (copy 2): f___collection_type_and_database_id_to_entry_cache_cache_key ]]
    return v_u_96:get(f___collection_type_and_database_id_to_entry_cache_cache_key(p99, p100));
end;
v_u_23.playerblob_get_collection_type_database_id_set = function(_, p101, p102, p103) --[[ Name: playerblob_get_collection_type_database_id_set ]] --[[ Line: 441 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_23 ]]
    local v104 = v_u_4:new()
    if p103 == nil then
        p103 = v_u_23:get_collection_info_from_playerblob(p101)
    end;
    for _, v105 in p103:get_collection_type_owned_entry_list(p102):key_itr() do
        v104:add_set(v105:get_database_id())
    end;
    return v104;
end;
v_u_23.get_playerblob_collection_type_database_id_owned = function(_, p106, p107, p108, p109) --[[ Name: get_playerblob_collection_type_database_id_owned ]] --[[ Line: 450 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    if p109 == nil then
        p109 = v_u_23:get_collection_info_from_playerblob(p106)
    end;
    local v110 = v_u_23:get_entry_for_collection_type_and_database_id(p107, p108)
    if v110 == nil then
        return false;
    else
        return p109:get_collection_type_and_id_owned(p107, (v110:get_collection_id()));
    end;
end;
local v_u_111 = v_u_4:new()
v_u_23.get_collection_type_display_entry_count = function(_, p112) --[[ Name: get_collection_type_display_entry_count ]] --[[ Line: 459 ]]
    --[[ Upvalues: (copy 1): v_u_111 ]]
    return v_u_111:contains(p112) ~= true and 0 or v_u_111:get(p112);
end;
v_u_23.playerblob_get_collection_songkeys_set = function(_, p113, p114) --[[ Name: playerblob_get_collection_songkeys_set ]] --[[ Line: 465 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    return v_u_23:playerblob_get_collection_type_database_id_set(p113, v_u_23.Type.Songs, p114);
end;
v_u_23.playerblob_add_collection_songkeys_to_set = function(_, p115, p116, p117) --[[ Name: playerblob_add_collection_songkeys_to_set ]] --[[ Line: 466 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_23 ]]
    v_u_4:set_union(p116, v_u_23:playerblob_get_collection_songkeys_set(p115, p117), p116)
end;
v_u_23.get_playerblob_songkey_in_collection = function(_, p118, p119, p120) --[[ Name: get_playerblob_songkey_in_collection ]] --[[ Line: 467 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    return v_u_23:get_playerblob_collection_type_database_id_owned(p118, v_u_23.Type.Songs, p119, p120);
end;
v_u_23.get_playerblob_equipmentid_in_collection = function(_, p121, p122, p123) --[[ Name: get_playerblob_equipmentid_in_collection ]] --[[ Line: 468 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    return v_u_23:get_playerblob_collection_type_database_id_owned(p121, v_u_23.Type.Gear, p122, p123);
end;
local v_u_124 = {}
v_u_23.CollectionLeaderboardEntry = v_u_124
v_u_124.new = function(_, p_u_125, p_u_126) --[[ Name: new ]] --[[ Line: 474 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4, (copy 3): v_u_23 ]]
    v_u_5:is_int(p_u_125)
    v_u_5:is_string(p_u_126)
    local v127 = {}
    local v_u_128 = 0
    local v_u_129 = v_u_4:new()
    local v_u_130 = os.time()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 484 ]]
        --[[ Upvalues: (ref 1): v_u_23, (copy 2): v_u_129 ]]
        for v131, _ in v_u_23:get_all_collection_types_set():key_itr() do
            v_u_129:add(v131, 0)
        end;
    end;
    v127.set_overall_point_amount = function(_, p132) --[[ Name: set_overall_point_amount ]] --[[ Line: 490 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_128 ]]
        v_u_5:is_int(p132)
        v_u_128 = p132
    end;
    v127.set_type_point_amount = function(_, p133, p134) --[[ Name: set_type_point_amount ]] --[[ Line: 495 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_23, (copy 3): v_u_129 ]]
        v_u_5:is_int(p134)
        v_u_5:is_enum_member(p133, v_u_23.Type)
        v_u_129:add(p133, p134)
    end;
    v127.set_timestamp = function(_, p135) --[[ Name: set_timestamp ]] --[[ Line: 501 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_130 ]]
        v_u_5:is_int(p135)
        v_u_130 = p135
    end;
    v127.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 506 ]]
        --[[ Upvalues: (copy 1): p_u_125 ]]
        return p_u_125;
    end;
    v127.get_player_name = function(_) --[[ Name: get_player_name ]] --[[ Line: 507 ]]
        --[[ Upvalues: (copy 1): p_u_126 ]]
        return p_u_126;
    end;
    v127.get_overall_point_amount = function(_) --[[ Name: get_overall_point_amount ]] --[[ Line: 508 ]]
        --[[ Upvalues: (ref 1): v_u_128 ]]
        return v_u_128;
    end;
    v127.get_timestamp = function(_) --[[ Name: get_timestamp ]] --[[ Line: 509 ]]
        --[[ Upvalues: (ref 1): v_u_130 ]]
        return v_u_130;
    end;
    v127.get_type_point_amount = function(_, p136) --[[ Name: get_type_point_amount ]] --[[ Line: 510 ]]
        --[[ Upvalues: (copy 1): v_u_129 ]]
        return not v_u_129:contains(p136) and 0 or v_u_129:get(p136);
    end;
    v127.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 518 ]]
        --[[ Upvalues: (copy 1): p_u_125, (copy 2): p_u_126, (ref 3): v_u_128, (copy 4): v_u_129, (ref 5): v_u_130 ]]
        return {
            ["PlayerID"] = p_u_125,
            ["PlayerName"] = p_u_126,
            ["OverallPointAmount"] = v_u_128,
            ["TypeToPointAmount"] = v_u_129:get_table(),
            ["Timestamp"] = v_u_130
        };
    end;
    f_cons()
    return v127;
end;
v_u_124.from_table = function(_, p137) --[[ Name: from_table ]] --[[ Line: 532 ]]
    --[[ Upvalues: (copy 1): v_u_124, (copy 2): v_u_4 ]]
    local v138 = v_u_124:new(p137.PlayerID, p137.PlayerName)
    v138:set_overall_point_amount(p137.OverallPointAmount)
    for v139, v140 in v_u_4:new(p137.TypeToPointAmount):key_itr() do
        v138:set_type_point_amount(v139, v140)
    end;
    v138:set_timestamp(p137.Timestamp)
    return v138;
end;
v_u_124.table_to_list = function(_, p_u_141) --[[ Name: table_to_list ]] --[[ Line: 542 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_23, (copy 3): v_u_1 ]]
    local v_u_142 = v_u_3:new()
    for v_u_143 = 1, #p_u_141 do
        local v144, v145 = pcall(function() --[[ Line: 545 ]]
            --[[ Upvalues: (copy 1): v_u_142, (ref 2): v_u_23, (copy 3): p_u_141, (copy 4): v_u_143 ]]
            v_u_142:push_back(v_u_23.CollectionLeaderboardEntry:from_table(p_u_141[v_u_143]))
        end)
        if not v144 then
            v_u_1:warnf("CollectionLeaderboardEntry:table_to_list skipped[%d] err(%s)", v_u_143, v145)
        end;
    end;
    return v_u_142;
end;
v_u_124.list_to_table = function(_, p146) --[[ Name: list_to_table ]] --[[ Line: 555 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v147 = v_u_3:new()
    for v148 = 1, p146:count() do
        v147:push_back(p146:get(v148):to_table())
    end;
    return v147:get_table();
end;
local v_u_149 = {}
v_u_23.CollectionLeaderboardRankData = v_u_149
v_u_149.new = function(_, p_u_150) --[[ Name: new ]] --[[ Line: 567 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_23 ]]
    local v_u_151 = v_u_4:new()
    local v152 = {}
    for v153, _ in v_u_23:get_all_collection_types_set():key_itr() do
        v_u_151:add(v153, -1)
    end;
    v152.get_overall_rank = function(_) --[[ Name: get_overall_rank ]] --[[ Line: 575 ]]
        --[[ Upvalues: (copy 1): p_u_150 ]]
        return p_u_150;
    end;
    v152.get_category_to_rank = function(_) --[[ Name: get_category_to_rank ]] --[[ Line: 576 ]]
        --[[ Upvalues: (copy 1): v_u_151 ]]
        return v_u_151;
    end;
    v152.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 578 ]]
        --[[ Upvalues: (copy 1): p_u_150, (copy 2): v_u_151 ]]
        return {
            ["OverallRank"] = p_u_150,
            ["Category"] = v_u_151:get_table()
        };
    end;
    return v152;
end;
v_u_149.from_table = function(_, p154) --[[ Name: from_table ]] --[[ Line: 588 ]]
    --[[ Upvalues: (copy 1): v_u_149, (copy 2): v_u_3, (copy 3): v_u_5 ]]
    local l_OverallRank_0 = p154.OverallRank
    local v155 = v_u_149:new(typeof(l_OverallRank_0) ~= "number" and -1 or l_OverallRank_0)
    if typeof(p154.Category) == "table" then
        for v156, v157 in v_u_3:new(p154.Category):key_itr() do
            v_u_5:is_int(v157)
            v155:get_category_to_rank():add(v156, v157)
        end;
    end;
    return v155;
end;
(function() --[[ Line: 603 ]]
    --[[ Upvalues: (copy 1): v_u_23, (copy 2): v_u_4, (copy 3): v_u_1, (copy 4): v_u_72, (copy 5): v_u_91, (copy 6): v_u_96, (copy 7): v_u_8, (copy 8): v_u_5, (copy 9): v_u_9, (copy 10): v_u_10, (copy 11): v_u_11, (copy 12): v_u_7, (copy 13): v_u_12, (copy 14): v_u_13, (copy 15): v_u_111 ]]
    for v_u_158, _ in v_u_23:get_all_collection_types_set():key_itr() do
        local v_u_159 = v_u_4:new()
        local v_u_160 = v_u_4:new()
        local v_u_161 = 0
        local function f_add_entry(p162, p163, p164) --[[ Name: add_entry ]] --[[ Line: 608 ]]
            --[[ Upvalues: (copy 1): v_u_159, (copy 2): v_u_160, (ref 3): v_u_1, (ref 4): v_u_23, (copy 5): v_u_158, (ref 6): v_u_72, (ref 7): v_u_161, (ref 8): v_u_91, (ref 9): v_u_96 ]]
            if v_u_159:contains(p162) or v_u_160:contains(p164) then
                v_u_1:errf("duplicate id(%d,%d)", p162, p164)
            end;
            v_u_159:add_set(p162)
            v_u_160:add_set(p164)
            local v165 = v_u_23.Entry:new(v_u_158, p162, p163, p164)
            v_u_72:push_back_to(v_u_158, v165)
            if p163 ~= -1 then
                v_u_161 = v_u_161 + 1
            end;
            v_u_91:add(string.format("%d_%d", v_u_158, p162), v165)
            v_u_96:add(string.format("%d_%d", v_u_158, p164), v165)
        end;
        local v_u_166 = 1
        local function _() --[[ Name: alloc_display_id ]] --[[ Line: 631 ]]
            --[[ Upvalues: (ref 1): v_u_166 ]]
            local v167 = v_u_166
            v_u_166 = v_u_166 + 1
            return v167;
        end;
        if v_u_158 == v_u_23.Type.Dances then
            local v168 = v_u_166
            for v169 = 1, v_u_8:singleton():count() do
                v_u_5:is_true(v_u_8:singleton():contains_dance_for_id(v169) == true)
                local v170
                if v_u_8:singleton():is_dance_default_owned(v169) == true then
                    v170 = v168
                    v168 = -1
                else
                    v_u_166 = v168 + 1
                    v170 = v_u_166
                end;
                f_add_entry(v169, v168, v169)
                v168 = v170
            end;
        elseif v_u_158 == v_u_23.Type.Gear then
            local v171 = v_u_166
            for v172 = 1, v_u_9:singleton():count() do
                v_u_5:is_true(v_u_9:singleton():get_equipment_for_id(v172) ~= nil)
                local v173
                if v172 >= 7 then
                    v_u_166 = v171 + 1
                    v173 = v_u_166
                else
                    v173 = v171
                    v171 = -1
                end;
                f_add_entry(v172, v171, v172)
                v171 = v173
            end;
        elseif v_u_158 == v_u_23.Type.Minis then
            local v174 = v_u_166
            for v175 = 1, v_u_10:singleton():count() do
                v_u_5:is_true(v_u_10:singleton():contains_petid(v175))
                v_u_166 = v174 + 1
                f_add_entry(v175, v174, v175)
                v174 = v_u_166
            end;
        elseif v_u_158 == v_u_23.Type.Stages then
            local v176 = v_u_166
            for v177 = 1, v_u_11:singleton():count() do
                v_u_5:is_true(v_u_11:singleton():contains_stageid(v177))
                local v178
                if v_u_11:singleton():get_stage_info_for_id(v177):get_material_id() == v_u_7:invalid_material_id() then
                    v178 = v176
                    v176 = -1
                else
                    v_u_166 = v176 + 1
                    v178 = v_u_166
                end;
                f_add_entry(v177, v176, v177)
                v176 = v178
            end;
        elseif v_u_158 == v_u_23.Type.Icons then
            local v179 = v_u_166
            for v180 = 1, v_u_12:singleton():count() + 1 do
                if v_u_12:singleton():contains_fevericon_for_id(v180) then
                    local v181
                    if v_u_12:singleton():get_fevericon_for_id(v180):get_material_id() == v_u_7:invalid_material_id() then
                        v181 = v179
                        v179 = -1
                    else
                        v_u_166 = v179 + 1
                        v181 = v_u_166
                    end;
                    f_add_entry(v180, v179, v180)
                    v179 = v181
                end;
            end;
        elseif v_u_158 == v_u_23.Type.Songs then
            local v182 = v_u_166
            for v183 = 1, v_u_13:singleton():count() do
                v_u_5:is_true(v_u_13:singleton():contains_key(v183))
                local v184
                if v_u_13:singleton():key_get_audiomod(v183) == v_u_13.MOD_EASY or v_u_13:singleton():key_is_remix_flagged(v183) == true then
                    v184 = v182
                    v182 = -1
                else
                    v_u_166 = v182 + 1
                    v184 = v_u_166
                end;
                f_add_entry(v183, v182, v183)
                v182 = v184
            end;
        else
            v_u_1:errf("Unimplemented initialize database for collection type(%s)", (tostring(v_u_158)))
        end;
        v_u_111:add(v_u_158, v_u_161)
    end;
end)()
v_u_23.get_title_id_to_collection_point_amount = function(_) --[[ Name: get_title_id_to_collection_point_amount ]] --[[ Line: 714 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4 ]]
    return v_u_3:new({
        78,
        79,
        80,
        81,
        82,
        83,
        84,
        85,
        87,
        117,
        118,
        148,
        149
    }), v_u_4:new({
        [78] = 100,
        [79] = 500,
        [80] = 1000,
        [81] = 2000,
        [82] = 3000,
        [83] = 4000,
        [84] = 5000,
        [85] = 6000,
        [87] = 7000,
        [117] = 8000,
        [118] = 9000,
        [148] = 10000,
        [149] = 11000
    });
end;
return v_u_23;
