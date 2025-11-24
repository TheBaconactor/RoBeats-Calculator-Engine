-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
local v_u_6 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
local v_u_7 = require(game.ReplicatedStorage.Shared.APICooldown)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_9 = require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_10 = require(game.ReplicatedStorage.EditorGame.Server.ServerEditorGameManager_PublishedMapManager)
local v_u_11 = require(game.ReplicatedStorage.EditorGame.Server.ServerEditorGameManager_MapLikes)
local v_u_12 = require(game.ReplicatedStorage.EditorGame.Server.ServerEditorGameManager_Playing)
local v_u_13 = require(game.ReplicatedStorage.EditorGame.Data.EditorDifficultyCalculation)
local s_DataStoreService_0 = game:GetService("DataStoreService")
return {
    ["new"] = function(_, p_u_14) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_11, (copy 3): v_u_12, (copy 4): v_u_5, (copy 5): v_u_4, (copy 6): v_u_6, (copy 7): v_u_2, (copy 8): v_u_8, (copy 9): v_u_9, (copy 10): v_u_1, (copy 11): v_u_13, (copy 12): s_DataStoreService_0, (copy 13): v_u_7, (copy 14): v_u_3 ]]
        local v_u_15 = {}
        local function _(p16, p17, p18) --[[ Name: generate_custom_map_key ]] --[[ Line: 24 ]]
            return string.format("%s@%d@%d", string.lower(p16), p17, p18);
        end;
        local v_u_19 = nil
        v_u_15.get_published_map_manager = function(_) --[[ Name: get_published_map_manager ]] --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19;
        end;
        local v_u_20 = nil
        v_u_15.get_map_likes_manager = function(_) --[[ Name: get_map_likes_manager ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        local v_u_21 = nil
        v_u_15.get_playing_manager = function(_) --[[ Name: get_playing_manager ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21;
        end;
        local function _() --[[ Name: cons ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_10, (copy 3): p_u_14, (copy 4): v_u_15, (ref 5): v_u_20, (ref 6): v_u_11, (ref 7): v_u_21, (ref 8): v_u_12 ]]
            v_u_19 = v_u_10:new(p_u_14, v_u_15)
            v_u_20 = v_u_11:new(p_u_14, v_u_15)
            v_u_21 = v_u_12:new(p_u_14, v_u_15)
        end;
        v_u_15.start = function(p_u_22) --[[ Name: start ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_6, (ref 5): v_u_2, (ref 6): v_u_8, (ref 7): v_u_9, (ref 8): v_u_1, (ref 9): v_u_13, (ref 10): v_u_19, (ref 11): v_u_20, (ref 12): v_u_21 ]]
            p_u_14._evt:wait_on_event(v_u_5.EVT_Editor_GetPlayerRecent_Client, function(p_u_23) --[[ Line: 42 ]]
                --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_4, (ref 3): v_u_6, (ref 4): v_u_2, (ref 5): p_u_14, (ref 6): v_u_5 ]]
                p_u_22:datastore_get_player_recent_saved_map_info_list(v_u_4:get_player_id(p_u_23), function(p24) --[[ Line: 43 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_2, (ref 3): p_u_14, (ref 4): v_u_5, (copy 5): p_u_23 ]]
                    local v25 = v_u_6.SavedMapInfo:info_list_from_table(v_u_6.SavedMapInfo:info_list_to_table(p24))
                    v_u_2:remove_if(v25, function(p26) --[[ Line: 45 ]]
                        --[[ Upvalues: (ref 1): v_u_6 ]]
                        return v_u_6:validate_saved_map_info(p26) ~= true;
                    end)
                    p_u_14._evt:fire_event_to_client(v_u_5.EVT_Editor_GetPlayerRecent_Server, p_u_23, (v_u_6.SavedMapInfo:info_list_to_table(v25)))
                end)
            end)
            p_u_14._evt:wait_on_event(v_u_5.EVT_Editor_LoadCustomMap_Client, function(p_u_27, p_u_28) --[[ Line: 57 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_6, (ref 3): p_u_14, (ref 4): v_u_5, (copy 5): p_u_22, (ref 6): v_u_4, (ref 7): v_u_9 ]]
                v_u_8:is_string(p_u_28)
                local function f_response(p29, p30, p31, p32) --[[ Name: response ]] --[[ Line: 60 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_14, (ref 3): v_u_5, (copy 4): p_u_27 ]]
                    if p30 == nil then
                        p30 = v_u_6.CustomMapData:new()
                    end;
                    if p31 == nil then
                        p31 = v_u_6.SavedMapInfo:new()
                    end;
                    if p32 == nil then
                        p32 = v_u_6.LoadCustomMapAdditionalInfo:new()
                    end;
                    p_u_14._evt:fire_event_to_client(v_u_5.EVT_Editor_LoadCustomMap_Server, p_u_27, p29, p30:to_table(), p31:to_table(), p32:to_table())
                end;
                if v_u_6:validate_custom_map_key_components(p_u_28) ~= true then
                    return f_response(false);
                end;
                p_u_22:datastore_player_get_key_custom_map_saved_map_info(v_u_4:get_player_id(p_u_27), p_u_28, function(p_u_33, p_u_34, p_u_35) --[[ Line: 85 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (copy 2): f_response, (ref 3): v_u_9, (ref 4): p_u_22, (copy 5): p_u_28, (copy 6): p_u_27 ]]
                    if v_u_6:validate_saved_map_info(p_u_35) ~= true then
                        return f_response(false);
                    end;
                    local v_u_36 = v_u_9.Builder:new()
                    v_u_36:begin()
                    p_u_22:datastore_get_editable_saved_map_info_given_custom_map_data_key_no_cooldown(p_u_28, function(p37) --[[ Line: 94 ]]
                        --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_35, (copy 3): v_u_36 ]]
                        v_u_6.SavedMapInfo:write_editable_saved_map_info_from_src_to_dest(p37, p_u_35)
                        v_u_36:finish()
                    end)
                    local v_u_38 = v_u_6.LoadCustomMapAdditionalInfo:new()
                    v_u_36:begin()
                    p_u_22:get_map_likes_manager():datastore_player_query_has_liked_custom_map_key(p_u_27.UserId, p_u_28, function(p39) --[[ Line: 102 ]]
                        --[[ Upvalues: (copy 1): v_u_38, (copy 2): v_u_36 ]]
                        v_u_38:set_player_already_liked(p39)
                        v_u_36:finish()
                    end)
                    v_u_36:wait_for_finish(function() --[[ Line: 107 ]]
                        --[[ Upvalues: (ref 1): f_response, (copy 2): p_u_33, (copy 3): p_u_34, (copy 4): p_u_35, (copy 5): v_u_38 ]]
                        return f_response(p_u_33, p_u_34, p_u_35, v_u_38);
                    end)
                end)
            end)
            p_u_14._evt:wait_on_event(v_u_5.EVT_Editor_SaveCustomMap_Client, function(p_u_40, p41, p42) --[[ Line: 113 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1, (ref 3): p_u_14, (ref 4): v_u_5, (ref 5): v_u_6, (copy 6): p_u_22, (ref 7): v_u_13, (ref 8): v_u_9 ]]
                if v_u_4:is_dev_build() then
                    v_u_1:puts("EVT_Editor_SaveCustomMap_Client")
                end;
                local function f_response(p43, p44, p45) --[[ Name: response ]] --[[ Line: 116 ]]
                    --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_5, (copy 3): p_u_40 ]]
                    local v46
                    if p45 == nil then
                        v46 = nil
                    else
                        v46 = p45:to_table()
                    end;
                    p_u_14._evt:fire_event_to_client(v_u_5.EVT_Editor_SaveCustomMap_Server, p_u_40, p43, p44, v46)
                end;
                local v_u_47 = v_u_6.SavedMapInfo:from_table(p41)
                local v_u_48 = v_u_47:get_custom_map_data_key()
                if (function() --[[ Name: validate_input_custom_map_key ]] --[[ Line: 127 ]]
                    --[[ Upvalues: (ref 1): v_u_48, (ref 2): v_u_6, (copy 3): p_u_40, (copy 4): v_u_47 ]]
                    if v_u_48 == v_u_6.SavedMapInfo:get_default_custom_map_key() then
                        return true;
                    else
                        local v49, v50, v51, _ = v_u_6:validate_custom_map_key_components(v_u_48)
                        if v49 == true then
                            if v50 == string.lower(p_u_40.Name) then
                                return v51 == v_u_47:get_source_songkey();
                            else
                                return false;
                            end;
                        else
                            return false;
                        end;
                    end;
                end)() ~= true then
                    return f_response(false, string.format("Custom map key is invalid (%s)", v_u_48));
                end;
                local v_u_52 = v_u_6.CustomMapData:from_table(p42)
                local v53, v54 = v_u_6:saved_map_info_custom_map_data_passes_validation(v_u_47, v_u_52)
                if v53 ~= true then
                    return f_response(false, v54);
                end;
                local v_u_55 = v_u_4:get_player_id(p_u_40)
                local v_u_56 = v_u_47:get_custom_map_name()
                local v57 = #v_u_56 <= 0 and "" or v_u_4:filter_string(v_u_56, p_u_40, p_u_40)
                if v_u_56 ~= v57 then
                    return f_response(false, string.format("Custom map name did not pass moderation(%s)", v57));
                end;
                p_u_22:datastore_get_player_recent_saved_map_info_list(v_u_55, function(p_u_58) --[[ Line: 164 ]]
                    --[[ Upvalues: (copy 1): v_u_47, (copy 2): p_u_40, (ref 3): v_u_48, (ref 4): v_u_6, (copy 5): f_response, (ref 6): v_u_13, (copy 7): v_u_52, (ref 8): v_u_4, (copy 9): v_u_56, (ref 10): v_u_1, (ref 11): p_u_22, (copy 12): v_u_55, (ref 13): v_u_9 ]]
                    local function _(p59) --[[ Name: get_saved_map_info_of_key ]] --[[ Line: 165 ]]
                        --[[ Upvalues: (copy 1): p_u_58 ]]
                        for _, v60 in p_u_58:key_itr() do
                            if v60:get_custom_map_data_key() == p59 then
                                return v60;
                            end;
                        end;
                        return nil;
                    end;
                    local function f_generate_unique_custom_map_key() --[[ Name: generate_unique_custom_map_key ]] --[[ Line: 173 ]]
                        --[[ Upvalues: (copy 1): p_u_58, (ref 2): v_u_47, (ref 3): p_u_40 ]]
                        local v61 = 1
                        for _, v62 in p_u_58:key_itr() do
                            if v62:get_source_songkey() == v_u_47:get_source_songkey() then
                                v61 = v61 + 1
                            end;
                        end;
                        local v63 = string.format("%s@%d@%d", string.lower(p_u_40.Name), v_u_47:get_source_songkey(), v61)
                        -- ::l12:: (Possible bug with goto)
                        local v64 = v63
                        for _, v66 in p_u_58:key_itr() do
                            if v66:get_custom_map_data_key() == v63 then
                                -- ::l8:: (Possible bug with goto)
                                if v66 == nil then
                                    return v64;
                                end;
                                v61 = v61 + 1
                                v63 = string.format("%s@%d@%d", string.lower(nil), nil, nil)
                                continue;
                            end;
                        end;
                        local v66 = nil
                        break;
                    end;
                    local v67
                    if v_u_48 == v_u_6.SavedMapInfo:get_default_custom_map_key() then
                        v67 = true
                        v_u_48 = f_generate_unique_custom_map_key()
                    else
                        v67 = false
                    end;
                    local v68 = v_u_48
                    for _, v_u_77 in p_u_58:key_itr() do
                        if v_u_77:get_custom_map_data_key() == v68 then
                            -- ::l6:: (Possible bug with goto)
                            if v67 == true then
                                if v_u_77 ~= nil then
                                    return f_response(false, string.format("Custom map key already exists in your recent maps"));
                                end;
                                v_u_77 = v_u_6.SavedMapInfo:new()
                            elseif v_u_77 == nil then
                                return f_response(false, string.format("Custom map key does not exist in your recent maps"));
                            end;
                            v_u_77:set_source_songkey(v_u_47:get_source_songkey())
                            v_u_77:set_last_edit_time(os.time())
                            v_u_77:set_creator_name(p_u_40.Name)
                            v_u_77:set_creator_rbxid(p_u_40.UserId)
                            v_u_77:set_custom_map_data_key(v_u_48)
                            local v70 = v_u_13:editor_game_data_note_list_calculate_difficulty(v_u_52:get_notes())
                            if v_u_47:has_assigned_difficulty() then
                                local v71, v72 = v_u_6.SavedMapInfo:calc_difficulty_get_min_max_assigned_difficulty(v70)
                                v_u_77:set_assigned_difficulty(v_u_4:clamp(v_u_47:get_assigned_difficulty(), v71, v72))
                            else
                                v_u_77:set_assigned_difficulty(v70)
                            end;
                            if #v_u_56 > 0 then
                                v_u_77:set_custom_map_name(v_u_56)
                            else
                                v_u_77:set_custom_map_name(v_u_77:get_default_custom_map_name())
                            end;
                            p_u_58:remove(v_u_77)
                            if p_u_58:count() >= v_u_6.SavedMapInfo:get_max_recent_saved_map_info_count() then
                                local v73 = p_u_58:pop_front()
                                if v73:get_custom_map_data_key() ~= v_u_6.SavedMapInfo:get_default_custom_map_key() then
                                    local v_u_74 = v73:get_custom_map_data_key()
                                    v_u_4:spawn(function() --[[ Line: 240 ]]
                                        --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_74, (ref 3): p_u_40, (ref 4): v_u_1, (ref 5): p_u_22, (ref 6): v_u_55 ]]
                                        local _, v75, _, _ = v_u_6:validate_custom_map_key_components(v_u_74)
                                        if v75 ~= string.lower(p_u_40.Name) then
                                            return v_u_1:warnf("Custom map key is invalid (%s) player(%s)", v_u_74, p_u_40.Name);
                                        end;
                                        p_u_22:datastore_delete_key_custom_map_and_saved_map_info(v_u_55, v_u_74)
                                    end)
                                end;
                            end;
                            p_u_58:push_back(v_u_77)
                            local v_u_76 = v_u_9.Builder:new()
                            v_u_76:begin()
                            p_u_22:datastore_write_player_recent_saved_map_info_list(v_u_55, p_u_58, function() --[[ Line: 254 ]]
                                --[[ Upvalues: (copy 1): v_u_76 ]]
                                v_u_76:finish()
                            end)
                            v_u_76:begin()
                            p_u_22:datastore_write_key_custom_map_and_saved_map_info(v_u_55, v_u_48, v_u_52, v_u_77, function() --[[ Line: 258 ]]
                                --[[ Upvalues: (copy 1): v_u_76 ]]
                                v_u_76:finish()
                            end)
                            v_u_76:wait_for_finish(function() --[[ Line: 261 ]]
                                --[[ Upvalues: (ref 1): f_response, (ref 2): v_u_77 ]]
                                return f_response(true, "", v_u_77);
                            end)
                            return;
                        end;
                    end;
                    local v_u_77 = nil
                    break;
                end)
            end)
            p_u_14._evt:wait_on_event(v_u_5.EVT_Editor_GetCreatorData_Client, function(p_u_78, p_u_79) --[[ Line: 267 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_22, (ref 3): p_u_14, (ref 4): v_u_5 ]]
                v_u_8:is_number(p_u_79)
                p_u_22:datastore_get_creator_data(p_u_79, p_u_78.UserId ~= p_u_79 and "" or p_u_78.Name, function(p_u_80) --[[ Line: 274 ]]
                    --[[ Upvalues: (copy 1): p_u_79, (ref 2): p_u_14, (ref 3): v_u_5, (copy 4): p_u_78 ]]
                    if #p_u_80:get_creator_name() == 0 then
                        pcall(function() --[[ Line: 276 ]]
                            --[[ Upvalues: (copy 1): p_u_80, (ref 2): p_u_79 ]]
                            p_u_80:set_creator_name(game.Players:GetNameFromUserIdAsync(p_u_79))
                        end)
                    end;
                    p_u_14._evt:fire_event_to_client(v_u_5.EVT_Editor_GetCreatorData_Server, p_u_78, p_u_80:to_table())
                end)
            end)
            v_u_19:start()
            v_u_20:start()
            v_u_21:start()
        end;
        local v_u_81 = v_u_2:new()
        v_u_15.register_fn_on_update = function(_, p82) --[[ Name: register_fn_on_update ]] --[[ Line: 290 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_81 ]]
            v_u_8:is_function(p82)
            v_u_81:push_back(p82)
        end;
        v_u_15.update = function(_, p_u_83) --[[ Name: update ]] --[[ Line: 295 ]]
            --[[ Upvalues: (copy 1): v_u_81, (ref 2): v_u_4 ]]
            for v84 = 1, v_u_81:count() do
                local v_u_85 = v_u_81:get(v84)
                v_u_4:ptry(function() --[[ Line: 298 ]]
                    --[[ Upvalues: (copy 1): v_u_85, (copy 2): p_u_83 ]]
                    v_u_85(p_u_83)
                end)
            end;
        end;
        local v_u_86 = v_u_2:new()
        v_u_15.register_fn_on_disconnect = function(_, p87) --[[ Name: register_fn_on_disconnect ]] --[[ Line: 306 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_86 ]]
            v_u_8:is_function(p87)
            v_u_86:push_back(p87)
        end;
        v_u_15.player_disconnecting = function(_, p_u_88) --[[ Name: player_disconnecting ]] --[[ Line: 311 ]]
            --[[ Upvalues: (copy 1): v_u_86, (ref 2): v_u_4 ]]
            for v89 = 1, v_u_86:count() do
                local v_u_90 = v_u_86:get(v89)
                v_u_4:ptry(function() --[[ Line: 314 ]]
                    --[[ Upvalues: (copy 1): v_u_90, (copy 2): p_u_88 ]]
                    v_u_90(p_u_88)
                end)
            end;
        end;
        local v_u_91 = nil
        v_u_4:ptry(function() --[[ Line: 324 ]]
            --[[ Upvalues: (ref 1): v_u_91, (ref 2): s_DataStoreService_0 ]]
            v_u_91 = s_DataStoreService_0:GetDataStore("EditorGamePlayerRecentSavedMapInfo")
        end)
        local v_u_92 = v_u_7:new():set_cooldown(0.5)
        local v_u_93 = v_u_7:new():set_cooldown(5)
        local v_u_94 = v_u_3:new()
        local function _(p95) --[[ Name: key_player_id ]] --[[ Line: 332 ]]
            return string.format("pr_%d", p95);
        end;
        v_u_15.datastore_write_player_recent_saved_map_info_list = function(_, p_u_96, p_u_97, p_u_98) --[[ Name: datastore_write_player_recent_saved_map_info_list ]] --[[ Line: 334 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_93, (copy 3): p_u_14, (ref 4): v_u_91, (copy 5): v_u_94 ]]
            while p_u_97:count() > v_u_6.SavedMapInfo:get_max_recent_saved_map_info_count() do
                p_u_97:pop_front()
            end;
            v_u_93:queue_key_request(p_u_96, function() --[[ Line: 338 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_91, (copy 3): p_u_96, (ref 4): v_u_6, (copy 5): p_u_97, (ref 6): v_u_94, (copy 7): p_u_98 ]]
                p_u_14._datastore_api:do_datastore_set(v_u_91, string.format("pr_%d", p_u_96), v_u_6.SavedMapInfo:info_list_to_table(p_u_97), function() --[[ Line: 343 ]]
                    --[[ Upvalues: (ref 1): v_u_94, (ref 2): p_u_96, (ref 3): p_u_97, (ref 4): p_u_98 ]]
                    v_u_94:add(p_u_96, p_u_97)
                    if p_u_98 then
                        p_u_98()
                    end;
                end)
            end)
        end;
        v_u_15.datastore_get_player_recent_saved_map_info_list = function(_, p_u_99, p_u_100) --[[ Name: datastore_get_player_recent_saved_map_info_list ]] --[[ Line: 351 ]]
            --[[ Upvalues: (copy 1): v_u_94, (copy 2): v_u_92, (copy 3): p_u_14, (ref 4): v_u_91, (ref 5): v_u_6, (ref 6): v_u_2 ]]
            if v_u_94:contains(p_u_99) then
                return p_u_100(v_u_94:get(p_u_99));
            end;
            v_u_92:queue_key_request(p_u_99, function() --[[ Line: 356 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_91, (copy 3): p_u_99, (ref 4): v_u_6, (ref 5): v_u_2, (ref 6): v_u_94, (copy 7): p_u_100 ]]
                p_u_14._datastore_api:do_datastore_get(v_u_91, string.format("pr_%d", p_u_99), function(_, p101) --[[ Line: 360 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_2, (ref 3): v_u_94, (ref 4): p_u_99, (ref 5): p_u_100 ]]
                    local v102
                    if typeof(p101) == "table" then
                        v102 = v_u_6.SavedMapInfo:info_list_from_datastore_forward_compat_table(p101)
                    else
                        v102 = v_u_2:new()
                    end;
                    v_u_94:add(p_u_99, v102)
                    p_u_100(v102)
                end)
            end)
        end;
        v_u_15:register_fn_on_disconnect(function(p103) --[[ Line: 374 ]]
            --[[ Upvalues: (copy 1): v_u_94 ]]
            v_u_94:remove(p103)
        end)
        local v_u_104 = nil
        v_u_4:ptry(function() --[[ Line: 384 ]]
            --[[ Upvalues: (ref 1): v_u_104, (ref 2): s_DataStoreService_0 ]]
            v_u_104 = s_DataStoreService_0:GetDataStore("EditorGameCustomMapAndSavedMapInfo")
        end)
        local v_u_105 = v_u_7:new():set_cooldown(5)
        local v_u_106 = v_u_7:new():set_cooldown(0.5)
        v_u_15.datastore_write_key_custom_map_and_saved_map_info = function(_, p107, p_u_108, p_u_109, p_u_110, p_u_111) --[[ Name: datastore_write_key_custom_map_and_saved_map_info ]] --[[ Line: 391 ]]
            --[[ Upvalues: (copy 1): v_u_105, (copy 2): p_u_14, (ref 3): v_u_104 ]]
            v_u_105:queue_key_request(p107, function() --[[ Line: 392 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_104, (copy 3): p_u_108, (copy 4): p_u_109, (copy 5): p_u_110, (copy 6): p_u_111 ]]
                p_u_14._datastore_api:do_datastore_set(v_u_104, p_u_108, {
                    ["CustomMapData"] = p_u_109:to_table(),
                    ["SavedMapInfo"] = p_u_110:to_table()
                }, function() --[[ Line: 400 ]]
                    --[[ Upvalues: (ref 1): p_u_111 ]]
                    if p_u_111 then
                        p_u_111()
                    end;
                end)
            end)
        end;
        v_u_15.datastore_player_get_key_custom_map_saved_map_info = function(_, p112, p_u_113, p_u_114) --[[ Name: datastore_player_get_key_custom_map_saved_map_info ]] --[[ Line: 408 ]]
            --[[ Upvalues: (copy 1): v_u_106, (copy 2): p_u_14, (ref 3): v_u_104, (ref 4): v_u_6 ]]
            v_u_106:queue_key_request(p112, function() --[[ Line: 409 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_104, (copy 3): p_u_113, (ref 4): v_u_6, (copy 5): p_u_114 ]]
                p_u_14._datastore_api:do_datastore_get(v_u_104, p_u_113, function(_, p115) --[[ Line: 413 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_114 ]]
                    v_u_6.CustomMapData:new()
                    local v116 = v_u_6.SavedMapInfo:new()
                    local v117 = false
                    local v118
                    if typeof(p115) == "table" then
                        v118 = v_u_6.CustomMapData:from_table(p115.CustomMapData)
                        v116 = v_u_6.SavedMapInfo:from_datastore_forward_compat_table(p115.SavedMapInfo)
                        v117 = true
                    else
                        v118 = v_u_6.CustomMapData:new()
                    end;
                    p_u_114(v117, v118, v116)
                end)
            end)
        end;
        v_u_15.datastore_delete_key_custom_map_and_saved_map_info = function(_, p119, p_u_120) --[[ Name: datastore_delete_key_custom_map_and_saved_map_info ]] --[[ Line: 430 ]]
            --[[ Upvalues: (copy 1): v_u_105, (copy 2): p_u_14, (ref 3): v_u_104 ]]
            v_u_105:queue_key_request(p119, function() --[[ Line: 431 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_104, (copy 3): p_u_120 ]]
                p_u_14._datastore_api:do_datastore_delete(v_u_104, p_u_120)
            end)
        end;
        local v_u_121 = nil
        v_u_4:ptry(function() --[[ Line: 444 ]]
            --[[ Upvalues: (ref 1): v_u_121, (ref 2): s_DataStoreService_0 ]]
            v_u_121 = s_DataStoreService_0:GetDataStore("EditorPublicEditableSavedMapInfo")
        end)
        local function _(p122) --[[ Name: custom_map_key_to_editable_saved_map_info ]] --[[ Line: 448 ]]
            return string.format("esm_%s", p122);
        end;
        v_u_15.datastore_write_editable_saved_map_info_with_action_no_cooldown = function(_, p_u_123, p_u_124, p_u_125) --[[ Name: datastore_write_editable_saved_map_info_with_action_no_cooldown ]] --[[ Line: 451 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_1, (copy 3): p_u_14, (ref 4): v_u_121 ]]
            if v_u_6:validate_custom_map_key_components(p_u_123:get_custom_map_data_key()) ~= true then
                return v_u_1:warnf("Invalid custom map key (%s) for datastore_write_editable_saved_map_info_with_action_no_cooldown", p_u_123:get_custom_map_data_key());
            end;
            p_u_14._datastore_api:do_datastore_update(v_u_121, string.format("esm_%s", (p_u_123:get_custom_map_data_key())), function(p126) --[[ Line: 458 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_124, (copy 3): p_u_123 ]]
                local v127
                if p126 == nil then
                    v127 = v_u_6.SavedMapInfo:new()
                else
                    v127 = v_u_6.SavedMapInfo:from_datastore_forward_compat_table(p126)
                end;
                p_u_124(v127)
                v_u_6.SavedMapInfo:write_editable_saved_map_info_from_src_to_dest(v127, p_u_123)
                return v127:to_table();
            end, function() --[[ Line: 470 ]]
                --[[ Upvalues: (copy 1): p_u_125, (copy 2): p_u_123 ]]
                if p_u_125 then
                    p_u_125(p_u_123)
                end;
            end)
        end;
        v_u_15.datastore_get_editable_saved_map_info_given_custom_map_data_key_no_cooldown = function(_, p128, p_u_129) --[[ Name: datastore_get_editable_saved_map_info_given_custom_map_data_key_no_cooldown ]] --[[ Line: 478 ]]
            --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_121, (ref 3): v_u_6 ]]
            p_u_14._datastore_api:do_datastore_get(v_u_121, string.format("esm_%s", p128), function(_, p130) --[[ Line: 482 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_129 ]]
                local v131
                if p130 == nil then
                    v131 = v_u_6.SavedMapInfo:new()
                else
                    v131 = v_u_6.SavedMapInfo:from_datastore_forward_compat_table(p130)
                end;
                if p_u_129 then
                    p_u_129(v131)
                end;
            end)
        end;
        local v_u_132 = nil
        v_u_4:ptry(function() --[[ Line: 500 ]]
            --[[ Upvalues: (ref 1): v_u_132, (ref 2): s_DataStoreService_0 ]]
            v_u_132 = s_DataStoreService_0:GetDataStore("EditorGameCreatorData")
        end)
        local v_u_133 = v_u_7:new():set_cooldown(3)
        local v_u_134 = v_u_7:new():set_cooldown(1.5)
        local function _(p135) --[[ Name: creator_rbxid_to_creator_data ]] --[[ Line: 507 ]]
            return string.format("ecd_%d", p135);
        end;
        v_u_15.datastore_write_creator_data = function(_, p_u_136, p_u_137, p_u_138) --[[ Name: datastore_write_creator_data ]] --[[ Line: 509 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_133, (copy 3): p_u_14, (ref 4): v_u_132, (ref 5): v_u_6 ]]
            v_u_8:is_number(p_u_136)
            v_u_8:is_string(p_u_137)
            v_u_133:queue_key_request(p_u_136, function() --[[ Line: 513 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_132, (copy 3): p_u_136, (ref 4): v_u_6, (copy 5): p_u_137, (copy 6): p_u_138 ]]
                p_u_14._datastore_api:do_datastore_update(v_u_132, string.format("ecd_%d", p_u_136), function(p139) --[[ Line: 517 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_137, (ref 3): p_u_136, (ref 4): p_u_138 ]]
                    local v140
                    if p139 == nil then
                        v140 = v_u_6.CreatorData:new()
                        v140:set_creator_name(p_u_137)
                        v140:set_creator_rbxid(p_u_136)
                    else
                        v140 = v_u_6.CreatorData:from_datastore_forward_compat_table(p139)
                    end;
                    if p_u_138(v140) == false then
                        return nil;
                    else
                        return v140:to_table();
                    end;
                end)
            end)
        end;
        v_u_15.datastore_get_creator_data = function(_, p_u_141, p_u_142, p_u_143) --[[ Name: datastore_get_creator_data ]] --[[ Line: 537 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_134, (copy 3): p_u_14, (ref 4): v_u_132, (ref 5): v_u_6 ]]
            v_u_8:is_number(p_u_141)
            v_u_8:is_string(p_u_142)
            v_u_134:queue_key_request(p_u_141, function() --[[ Line: 542 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_132, (copy 3): p_u_141, (ref 4): v_u_6, (copy 5): p_u_142, (copy 6): p_u_143 ]]
                p_u_14._datastore_api:do_datastore_get(v_u_132, string.format("ecd_%d", p_u_141), function(_, p144) --[[ Line: 546 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_142, (ref 3): p_u_141, (ref 4): p_u_143 ]]
                    local v145
                    if p144 == nil then
                        v145 = v_u_6.CreatorData:new()
                        v145:set_creator_name(p_u_142)
                        v145:set_creator_rbxid(p_u_141)
                    else
                        v145 = v_u_6.CreatorData:from_datastore_forward_compat_table(p144)
                    end;
                    if p_u_143 then
                        p_u_143(v145)
                    end;
                end)
            end)
        end;
        local _ = v_u_10:new(p_u_14, v_u_15)
        local _ = v_u_11:new(p_u_14, v_u_15)
        local _ = v_u_12:new(p_u_14, v_u_15)
        return v_u_15;
    end
};
