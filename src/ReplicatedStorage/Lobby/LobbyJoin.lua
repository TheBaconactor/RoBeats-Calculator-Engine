-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:31 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Lobby.LobbyLocal)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_2 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Local.GameJoin)
require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.Lobby.CharacterManager)
return {
    ["new"] = function(_, p_u_6) --[[ Name: new ]] --[[ Line: 17 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_1, (copy 5): v_u_3 ]]
        local v7 = {}
        local v_u_8 = nil
        v7.get_lobby = function(_) --[[ Name: get_lobby ]] --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            return v_u_8;
        end;
        local v_u_9 = false
        local v_u_10 = v_u_5:new(p_u_6)
        v7.get_character_manager = function(_) --[[ Name: get_character_manager ]] --[[ Line: 26 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            return v_u_10;
        end;
        local v_u_11 = nil
        local v_u_12 = nil
        local v_u_13 = nil
        v7.get_song_shop_center_position = function(_) --[[ Name: get_song_shop_center_position ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11.Position;
        end;
        v7.get_gear_shop_center_position = function(_) --[[ Name: get_gear_shop_center_position ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            return v_u_12.Position;
        end;
        v7.get_compete_building_position = function(_) --[[ Name: get_compete_building_position ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return v_u_13.Position;
        end;
        local function _() --[[ Name: cons ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_2, (ref 3): v_u_12, (ref 4): v_u_13 ]]
            v_u_11 = v_u_2:get_lobby_anchors().Shop.Center
            v_u_12 = v_u_2:get_lobby_anchors().GearShop.Center
            v_u_13 = v_u_2:get_lobby_anchors().CompeteBuilding.Center
        end;
        local v_u_14 = v_u_4:new()
        v7.get_registered_lobby_join_update_fns = function(_) --[[ Name: get_registered_lobby_join_update_fns ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): v_u_14 ]]
            return v_u_14;
        end;
        v7.register_lobby_join_update_fn = function(_, p15) --[[ Name: register_lobby_join_update_fn ]] --[[ Line: 44 ]]
            --[[ Upvalues: (copy 1): v_u_14 ]]
            v_u_14:push_back(p15)
        end;
        local v_u_16 = v_u_4:new()
        local v_u_17 = v_u_4:new()
        v7.register_lobby_join_start_fn = function(_, p18) --[[ Name: register_lobby_join_start_fn ]] --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): v_u_16 ]]
            v_u_16:push_back(p18)
        end;
        v7.register_lobby_join_exit_fn = function(_, p19) --[[ Name: register_lobby_join_exit_fn ]] --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): v_u_17 ]]
            v_u_17:push_back(p19)
        end;
        v7.get_registered_lobby_join_start_fns = function(_) --[[ Name: get_registered_lobby_join_start_fns ]] --[[ Line: 51 ]]
            --[[ Upvalues: (copy 1): v_u_16 ]]
            return v_u_16;
        end;
        v7.setup_lobby = function(p20) --[[ Name: setup_lobby ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_1, (copy 3): p_u_6, (ref 4): v_u_9, (ref 5): v_u_3, (ref 6): v_u_2, (copy 7): v_u_10 ]]
            v_u_8 = v_u_1:new(p_u_6, p20)
            v_u_9 = true
            local v21, v22 = v_u_3:is_event_active(v_u_8._player_blob_manager:get_day_event_list())
            if v21 and v22 == 11 then
                v_u_2:set_mode(v_u_2.Mode.LobbyHalloween)
            else
                v_u_2:set_mode(v_u_2.Mode.Lobby)
            end;
            p_u_6._input:set_keyboard_focused_mode(false)
            v_u_10:create_nametags_for_existing_players()
        end;
        v7.start_lobby = function(_) --[[ Name: start_lobby ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_2 ]]
            v_u_8:start_lobby()
            v_u_2:should_load_textures(true)
        end;
        v7.update = function(_, p23) --[[ Name: update ]] --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_8 ]]
            if v_u_9 then
                v_u_8:update(p23)
            end;
        end;
        v7.post_update = function(_, p24) --[[ Name: post_update ]] --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (copy 3): v_u_10 ]]
            if v_u_8 ~= nil then
                if v_u_9 then
                    v_u_8:post_update(p24)
                    v_u_10:update(p24)
                end;
            end;
        end;
        v7.push_ui_to_lobby = function(_, p25) --[[ Name: push_ui_to_lobby ]] --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8:enqueue_loaded_callback(p25)
        end;
        v7.teardown_lobby = function(_) --[[ Name: teardown_lobby ]] --[[ Line: 94 ]]
            --[[ Upvalues: (copy 1): v_u_17, (ref 2): v_u_8, (ref 3): v_u_9 ]]
            for _, v26 in v_u_17:key_itr() do
                v26(v_u_8)
            end;
            if v_u_8 ~= nil then
                v_u_8:cache_character_cframe()
                v_u_8:cleanup()
            end;
            v_u_9 = false
            v_u_8 = nil
        end;
        local v_u_27 = false
        local v_u_28 = CFrame.new()
        v7.has_cached_character_cframe = function(_) --[[ Name: has_cached_character_cframe ]] --[[ Line: 108 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27;
        end;
        v7.get_cached_character_cframe = function(_) --[[ Name: get_cached_character_cframe ]] --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28;
        end;
        v7.set_cached_character_cframe = function(_, p29) --[[ Name: set_cached_character_cframe ]] --[[ Line: 110 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_28 ]]
            v_u_27 = true
            v_u_28 = p29
        end;
        v7.reset_cached_character_cframe = function(_) --[[ Name: reset_cached_character_cframe ]] --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            v_u_27 = false
        end;
        local v_u_30 = v_u_4:new()
        v7.save_restore_menu_names = function(_) --[[ Name: save_restore_menu_names ]] --[[ Line: 117 ]]
            --[[ Upvalues: (copy 1): v_u_30, (copy 2): p_u_6 ]]
            v_u_30:clear()
            for _, v31 in p_u_6._menus:get_menu_stack():key_itr() do
                if v31:get_restore_name() ~= nil then
                    v_u_30:push_back(v31:get_restore_name())
                end;
            end;
        end;
        v7.clear_restore_menu_names = function(_) --[[ Name: clear_restore_menu_names ]] --[[ Line: 127 ]]
            --[[ Upvalues: (copy 1): v_u_30 ]]
            v_u_30:clear()
        end;
        v7.get_restore_menu_names = function(_) --[[ Name: get_restore_menu_names ]] --[[ Line: 128 ]]
            --[[ Upvalues: (copy 1): v_u_30 ]]
            return v_u_30;
        end;
        v7.save_camera_position = function(_) --[[ Name: save_camera_position ]] --[[ Line: 130 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            if v_u_8 then
                v_u_8:save_camera_position()
            end;
        end;
        v_u_11 = v_u_2:get_lobby_anchors().Shop.Center
        v_u_12 = v_u_2:get_lobby_anchors().GearShop.Center
        v_u_13 = v_u_2:get_lobby_anchors().CompeteBuilding.Center
        return v7;
    end
};
