-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:34 PM
-- Time elapsed: 9 milliseconds

require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_2 = require(game.ReplicatedStorage.Local.DebugOut)
local v3 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_4 = nil
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
v3:require_client(function() --[[ Line: 16 ]]
    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): v_u_7, (ref 5): v_u_8, (ref 6): v_u_9, (ref 7): v_u_10, (ref 8): v_u_11, (ref 9): v_u_12 ]]
    v_u_4 = require(game.ReplicatedStorage.Lobby.Menus.LobbyHUDV2UI)
    v_u_5 = require(game.ReplicatedStorage.Lobby.Menus.SettingsUI)
    v_u_6 = require(game.ReplicatedStorage.Lobby.Menus.PlayUI)
    v_u_7 = require(game.ReplicatedStorage.Lobby.Menus.ArtistEventUI)
    v_u_8 = require(game.ReplicatedStorage.Lobby.Menus.SongShopUI)
    v_u_9 = require(game.ReplicatedStorage.Lobby.LobbySpectateManager)
    v_u_10 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI)
    v_u_11 = require(game.ReplicatedStorage.EditorGame.UI.SavedMapInfoListUI)
    v_u_12 = require(game.ReplicatedStorage.Lobby.Menus.MissionUI)
end)
return {
    ["new"] = function(_, p_u_13, p_u_14) --[[ Name: new ]] --[[ Line: 30 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_7, (ref 4): v_u_8, (ref 5): v_u_9, (ref 6): v_u_10, (ref 7): v_u_11, (copy 8): v_u_2, (ref 9): v_u_4, (copy 10): v_u_1 ]]
        local v15 = {
            ["update"] = function(_, _, _) end
        }
        local v_u_16 = nil
        local function f_restore_menu_from_name(p17) --[[ Name: restore_menu_from_name ]] --[[ Line: 35 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): v_u_7, (ref 5): v_u_8, (ref 6): v_u_9, (ref 7): v_u_10, (ref 8): v_u_11, (copy 9): p_u_14, (ref 10): v_u_2 ]]
            local l__spui_0 = p_u_13._spui
            local l__menus_0 = p_u_13._menus
            if p17 == v_u_5:get_restore_menu_name() then
                l__menus_0:push_menu(v_u_5:new(p_u_13, l__spui_0, l__menus_0))
                return;
            elseif p17 == v_u_6:get_restore_menu_name() then
                l__menus_0:push_menu(v_u_6:new(p_u_13, l__spui_0, l__menus_0))
                return;
            elseif p17 == v_u_7:get_restore_menu_name() then
                l__menus_0:push_menu(v_u_7:new(p_u_13, l__spui_0, l__menus_0))
                return;
            elseif p17 == v_u_8:get_restore_menu_name() then
                l__menus_0:push_menu(v_u_8:new(p_u_13, l__spui_0, l__menus_0))
                return;
            elseif p17 == v_u_9:get_song_select_preview_menu_restore_name() then
                p_u_13._spectate_manager:show_song_select_preview_menu()
                return;
            elseif p17 == v_u_10:get_restore_menu_name() then
                l__menus_0:push_menu(v_u_10:new(p_u_13):load_custom_map_note_data())
                return;
            elseif p17 == v_u_11:get_editor_menu_restore_menu_name() then
                v_u_11:show_editor_menu(p_u_14)
            else
                v_u_2:puts("LobbyUIManager:restore_menu_from_name unknown menu name(%s)", p17)
            end;
        end;
        local function f_restore_menus() --[[ Name: restore_menus ]] --[[ Line: 59 ]]
            --[[ Upvalues: (copy 1): p_u_14, (copy 2): f_restore_menu_from_name ]]
            for _, v18 in p_u_14._lobby_join:get_restore_menu_names():key_itr() do
                f_restore_menu_from_name(v18)
            end;
            p_u_14._lobby_join:clear_restore_menu_names()
        end;
        v15.initialize_ui = function(_, _) --[[ Name: initialize_ui ]] --[[ Line: 66 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_16, (ref 3): v_u_4, (copy 4): f_restore_menus ]]
            p_u_13._spui:layout()
            v_u_16 = p_u_13._menus:push_menu(v_u_4:new(p_u_13, p_u_13._spui, p_u_13._menus))
            p_u_13._spui:layout()
            f_restore_menus()
        end;
        v15.get_hud_ui = function(_) --[[ Name: get_hud_ui ]] --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            return v_u_16;
        end;
        v15.swallow_control_input = function(_) --[[ Name: swallow_control_input ]] --[[ Line: 78 ]]
            --[[ Upvalues: (copy 1): p_u_14 ]]
            if p_u_14._game_join:get_game() == nil then
                for _, v19 in p_u_14._menus:get_menus_to_push():key_itr() do
                    if v19:swallows_input() then
                        return true;
                    end;
                end;
                local v20 = p_u_14._menus:get_top_element()
                if v20 == nil then
                    return false;
                else
                    return v20:swallows_input();
                end;
            else
                return true;
            end;
        end;
        v15.handles_bgm = function(_) --[[ Name: handles_bgm ]] --[[ Line: 94 ]]
            --[[ Upvalues: (copy 1): p_u_13 ]]
            local v21 = p_u_13._menus:get_top_element()
            if v21 == nil then
                return false;
            else
                return v21:handles_bgm();
            end;
        end;
        local v_u_22 = v_u_1:new():add_set_from_table_list({ v_u_8:get_restore_menu_name() })
        v15.remove_menus_with_anchors = function(_, p23) --[[ Name: remove_menus_with_anchors ]] --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_13, (copy 3): v_u_22 ]]
            if p23 == nil then
                p23 = v_u_1:new()
            end;
            local v24 = p_u_13._menus:get_menu_stack()
            for v25 = v24:count(), 1, -1 do
                local v26 = v24:get(v25)
                local v27 = v26:get_restore_name()
                if p23:contains(v27) ~= true and v_u_22:contains(v27) == true then
                    p_u_13._menus:remove_menu(v26)
                end;
            end;
        end;
        return v15;
    end
};
