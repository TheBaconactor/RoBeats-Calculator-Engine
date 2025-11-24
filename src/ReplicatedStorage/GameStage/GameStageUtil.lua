-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:05 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_3 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v8 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
v8:require_shared(function() --[[ Line: 18 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_13, (ref 6): v_u_14, (ref 7): v_u_15 ]]
    v_u_9 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
    v_u_10 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
    v_u_11 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
    v_u_12 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistEventInfo)
    v_u_13 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP2EventInfo)
    v_u_14 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP3EventInfo)
    v_u_15 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.Black17EventInfo)
end)
local v_u_23 = {
    ["get_recommended_stage_id"] = function(_) --[[ Name: get_recommended_stage_id ]] --[[ Line: 31 ]]
        return -1;
    end,
    ["playerblob_get_owned_stage_ids_set"] = function(_, p16, p17) --[[ Name: playerblob_get_owned_stage_ids_set ]] --[[ Line: 38 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_6, (copy 6): v_u_7, (ref 7): v_u_9 ]]
        local v18 = v_u_4:new()
        for v19, _ in v_u_2:get_owned_crafting_materials(p16):key_itr() do
            local v20 = v_u_3:singleton():get_material(v19)
            if v20 and v_u_3:singleton():get_material_type(v19) == v_u_5.Type.Stage then
                v18:add_set(v20:get_stage_id())
            end;
        end;
        for v21, _ in v_u_6:playerblob_get_collection_type_database_id_set(p16, v_u_6.Type.Stages, p17):key_itr() do
            v18:add_set(v21)
        end;
        if v_u_7.PlayerBlobDebugOwnsAllStages == true then
            for v22 = 1, v_u_9:singleton():count() do
                if v_u_9:singleton():contains_stageid(v22) then
                    v18:add_set(v22)
                end;
            end;
        end;
        return v18;
    end
}
v_u_23.is_valid_stage_id = function(_, p24) --[[ Name: is_valid_stage_id ]] --[[ Line: 33 ]]
    --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_9 ]]
    return p24 == v_u_23:get_recommended_stage_id() and true or v_u_9:singleton():get_stage_info_for_id(p24) ~= nil;
end;
v_u_23.playerblob_get_available_stage_ids_set_for_day_event_list_and_event_info = function(_, p25, p26, p27, p28) --[[ Name: playerblob_get_available_stage_ids_set_for_day_event_list_and_event_info ]] --[[ Line: 63 ]]
    --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_9, (ref 3): v_u_11, (ref 4): v_u_10, (ref 5): v_u_15 ]]
    local v29 = v_u_23:playerblob_get_owned_stage_ids_set(p25, p28)
    v29:add_set(v_u_9:singleton():get_default_stage_id())
    v29:add_set(v_u_9:singleton():get_default_dark_stage_id())
    if p27 == v_u_11.EventMission.ArtistEvent then
        local v30, v31 = v_u_10:is_event_active(p26)
        if v30 and v_u_10:get_event_info(v31) then
            local v32 = v_u_10:get_event_info(v31)
            if v32:has_stage() then
                v29:add_set(v32:get_stage_id())
            end;
        end;
    end;
    if p27 == v_u_11.EventMission.Black17Event then
        v29:add_set(v_u_15:get_stage_id())
    end;
    return v29;
end;
v_u_23.playerblob_get_available_stage_ids_list_for_day_event_list_and_event_info = function(_, p33, p34, p35, p36) --[[ Name: playerblob_get_available_stage_ids_list_for_day_event_list_and_event_info ]] --[[ Line: 95 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    local v37 = v_u_23:playerblob_get_available_stage_ids_set_for_day_event_list_and_event_info(p33, p34, p35, p36):key_list()
    v37:sort(function(p38, p39) --[[ Line: 102 ]]
        return p39 - p38;
    end)
    return v37;
end;
v_u_23.resolve_stage_id_for_playerblob_day_event_list_and_event_info = function(_, p40, p41, p42, p43, p44) --[[ Name: resolve_stage_id_for_playerblob_day_event_list_and_event_info ]] --[[ Line: 108 ]]
    --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_9 ]]
    if v_u_23:playerblob_get_available_stage_ids_set_for_day_event_list_and_event_info(p41, p42, p43, p44):contains(p40) then
        return p40;
    else
        return v_u_9:singleton():get_default_stage_id();
    end;
end;
v_u_23.get_name_for_stage_id = function(_, p45) --[[ Name: get_name_for_stage_id ]] --[[ Line: 122 ]]
    --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_9 ]]
    return p45 == v_u_23:get_recommended_stage_id() and "Recommended" or v_u_9:singleton():get_stage_info_for_id(p45):get_name();
end;
v_u_23.get_icon_for_stage_id = function(_, p46) --[[ Name: get_icon_for_stage_id ]] --[[ Line: 130 ]]
    --[[ Upvalues: (copy 1): v_u_23, (copy 2): v_u_1, (ref 3): v_u_9 ]]
    if p46 == v_u_23:get_recommended_stage_id() then
        return v_u_1:get_question_assetid();
    else
        return v_u_9:singleton():get_stage_info_for_id(p46):get_icon();
    end;
end;
return v_u_23;
