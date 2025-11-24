-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:47 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.MaterialsRequiredDisplay)
local v_u_13 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_14 = require(game.ReplicatedStorage.Lobby.UI.UIToggleGroup)
local v_u_15 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_16 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v19 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_20 = nil
local v_u_21 = nil
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
local v_u_25 = nil
local v_u_26 = nil
v19:require_client(function() --[[ Line: 32 ]]
    --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21, (ref 3): v_u_22, (ref 4): v_u_23, (ref 5): v_u_24, (ref 6): v_u_25, (ref 7): v_u_26 ]]
    v_u_20 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.CraftingGatchaUI)
    v_u_22 = require(game.ReplicatedStorage.Lobby.Menus.MarketplaceUI)
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.CraftingUI)
    v_u_24 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabCraftMaterials)
    v_u_25 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabMaterials)
    v_u_26 = require(game.ReplicatedStorage.Lobby.Menus.SongAcquiredV2UI)
end)
local v_u_30 = {
    ["get_songkey_recipe_id"] = function(_, p27) --[[ Name: get_songkey_recipe_id ]] --[[ Line: 44 ]]
        --[[ Upvalues: (copy 1): v_u_15, (copy 2): v_u_16, (copy 3): v_u_9 ]]
        local v28 = v_u_15:singleton():get_audiomod_to_modes_of_songkey(p27):get(v_u_16.Normal)
        local v29
        if v_u_15:singleton():contains_key(v28) then
            v29 = v_u_9:singleton():get_songkey_recipe_id(v28)
        else
            v29 = nil
        end;
        return v29, v28;
    end
}
v_u_30.new = function(_, p_u_31, p_u_32, p_u_33, p_u_34, p_u_35) --[[ Name: new ]] --[[ Line: 53 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_15, (copy 3): v_u_16, (copy 4): v_u_30, (copy 5): v_u_13, (ref 6): v_u_20, (copy 7): v_u_3, (copy 8): v_u_17, (copy 9): v_u_1, (copy 10): v_u_18, (copy 11): v_u_10, (copy 12): v_u_5, (copy 13): v_u_6, (copy 14): v_u_7, (ref 15): v_u_21, (copy 16): v_u_11, (ref 17): v_u_22, (ref 18): v_u_23, (ref 19): v_u_25, (copy 20): v_u_12, (copy 21): v_u_14, (ref 22): v_u_26, (copy 23): v_u_2, (copy 24): v_u_9, (copy 25): v_u_8 ]]
    local v_u_36 = v_u_4:new(p_u_32, p_u_33)
    p_u_33:remove_menu_if(function(p37) --[[ Line: 57 ]]
        return p37.__type_key == "CraftSongUI";
    end)
    v_u_36.__type_key = "CraftSongUI"
    if v_u_15:singleton():get_songkey_should_grant(p_u_34) ~= true then
        p_u_34 = v_u_15:singleton():get_audiomod_to_modes_of_songkey(p_u_34):get(v_u_16.Normal)
    end;
    local v_u_38, v_u_39 = v_u_30:get_songkey_recipe_id(p_u_34)
    if v_u_38 == nil or v_u_13:can_craft_recipe(p_u_31._player_blob_manager:get_player_blob(), v_u_38) ~= true then
        return v_u_20:new(p_u_31, p_u_32, p_u_33):set_text("Error", "Cannot craft this song");
    end;
    local v_u_40 = nil
    local v_u_41 = nil
    local v_u_42 = v_u_3:new()
    local v_u_43 = nil
    local v_u_44 = true
    local function f_get_craft_amount() --[[ Name: get_craft_amount ]] --[[ Line: 80 ]]
        --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_15, (ref 3): p_u_34, (ref 4): v_u_16, (ref 5): v_u_44, (ref 6): v_u_17, (copy 7): v_u_39 ]]
        return v_u_15:singleton():key_get_audiomod(p_u_34) ~= v_u_16.Hard and 1 or math.max((v_u_44 and 6 or 5) - v_u_17:get_song_key_owned_count(p_u_31._player_blob_manager:get_player_blob(), v_u_39), 0);
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 92 ]]
        --[[ Upvalues: (ref 1): v_u_40, (ref 2): v_u_1, (copy 3): v_u_36, (copy 4): p_u_31, (ref 5): v_u_18, (copy 6): v_u_39, (ref 7): v_u_44, (ref 8): v_u_41, (ref 9): v_u_10, (ref 10): v_u_5, (ref 11): p_u_34, (ref 12): v_u_6, (copy 13): p_u_32, (ref 14): v_u_7, (copy 15): p_u_33, (ref 16): v_u_21, (ref 17): v_u_11, (ref 18): v_u_22, (ref 19): v_u_23, (ref 20): v_u_25, (copy 21): v_u_42, (ref 22): v_u_12, (ref 23): v_u_15, (ref 24): v_u_16, (ref 25): v_u_14, (ref 26): v_u_3, (ref 27): v_u_43, (copy 28): v_u_38, (ref 29): v_u_20, (ref 30): v_u_26, (copy 31): p_u_35, (copy 32): f_get_craft_amount, (ref 33): v_u_2, (ref 34): v_u_30, (ref 35): v_u_13 ]]
        v_u_40 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Util.CraftSongUI:Clone()
        v_u_40.Name = v_u_1:gen_name(v_u_40.Name)
        v_u_36:set_showing(true)
        local v45 = p_u_31._player_blob_manager:get_player_blob()
        if v_u_18:get_playerblob_songkey_in_collection(v45, v_u_39, p_u_31._player_blob_manager:get_cached_collection_info()) == true then
            v_u_44 = false
        end;
        v_u_36._native_size = v_u_40.PrimaryPart.Size
        v_u_36._size = v_u_36._native_size
        v_u_41 = v_u_10:new(p_u_31, v_u_40.SongElementDisplay, v_u_5:new(v_u_36, v_u_40.PrimaryPart, v_u_40.SongElementDisplay.PrimaryPart))
        v_u_41:display_song(p_u_34)
        v_u_36:add_cycle_element(p_u_31, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_40.PrimaryPart, v_u_40.BackButtonSurface), p_u_32, function() --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (ref 3): p_u_33, (ref 4): v_u_36 ]]
            p_u_31._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            p_u_33:remove_menu(v_u_36)
        end))
        v_u_36:add_cycle_element(p_u_31, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_40.PrimaryPart, v_u_40.SongInfoButton), p_u_32, function() --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (ref 3): v_u_10, (ref 4): p_u_34 ]]
            p_u_31._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_10:show_song_info_popup(p_u_31, p_u_34)
        end))
        v_u_36:add_cycle_element(p_u_31, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_40.PrimaryPart, v_u_40.NoteMachineButton), p_u_32, function() --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (ref 3): p_u_33, (ref 4): v_u_21, (ref 5): p_u_32 ]]
            p_u_31._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
            p_u_33:remove_all_menus_except(p_u_31._ui_manager:get_hud_ui())
            p_u_33:push_menu(v_u_21:new(p_u_31, p_u_32, p_u_33))
        end))
        v_u_36:add_cycle_element(p_u_31, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_40.PrimaryPart, v_u_40.MarketplaceButton), p_u_32, function() --[[ Line: 143 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (ref 3): p_u_33, (ref 4): v_u_11, (ref 5): v_u_22, (ref 6): p_u_32 ]]
            p_u_31._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
            p_u_33:remove_all_menus_except(p_u_31._ui_manager:get_hud_ui())
            if v_u_11.TradeEnabled == true then
                p_u_33:push_menu(v_u_22:new(p_u_31, p_u_32, p_u_33))
            end;
        end))
        v_u_36:add_cycle_element(p_u_31, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_40.PrimaryPart, v_u_40.CraftButton), p_u_32, function() --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (ref 3): p_u_33, (ref 4): v_u_23, (ref 5): p_u_32, (ref 6): v_u_25 ]]
            p_u_31._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
            p_u_33:push_menu(v_u_23:new(p_u_31, p_u_32, p_u_33, v_u_25.Tab))
        end))
        local l_LoadedSection_0 = v_u_40.MainSurface.SurfaceGui.Frame.LoadedSection
        v_u_42:push_back(v_u_12:new(l_LoadedSection_0.RequirementDisplay1))
        v_u_42:push_back(v_u_12:new(l_LoadedSection_0.RequirementDisplay2))
        v_u_42:push_back(v_u_12:new(l_LoadedSection_0.RequirementDisplay3))
        v_u_42:push_back(v_u_12:new(l_LoadedSection_0.RequirementDisplay4))
        if v_u_15:singleton():key_get_audiomod(p_u_34) == v_u_16.Hard then
            v_u_14:new(v_u_3:new():push_back_table_list({ v_u_40.KeepCopyOfNormalMode.True, v_u_40.KeepCopyOfNormalMode.False }), v_u_3:new():push_back_table_list({ true, false }), function(p46) --[[ Line: 170 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (ref 3): v_u_44, (ref 4): v_u_36 ]]
                p_u_31._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_44 = p46
                v_u_36:update_materials_required_display()
            end, function() --[[ Line: 175 ]]
                --[[ Upvalues: (ref 1): v_u_44 ]]
                return v_u_44;
            end, v_u_36, v_u_40.PrimaryPart, p_u_31, p_u_32)
        else
            v_u_40.KeepCopyOfNormalMode.True.Parent = nil
            v_u_40.KeepCopyOfNormalMode.False.Parent = nil
            l_LoadedSection_0.KeepCopyOfNormalModeSection.Visible = false
        end;
        v_u_43 = v_u_36:add_cycle_element(p_u_31, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_40.PrimaryPart, v_u_40.CraftSongButton), p_u_32, function() --[[ Line: 189 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (ref 3): v_u_38, (ref 4): v_u_39, (ref 5): p_u_33, (ref 6): v_u_36, (ref 7): v_u_20, (ref 8): p_u_32, (ref 9): v_u_26, (ref 10): p_u_35, (ref 11): f_get_craft_amount, (ref 12): v_u_15, (ref 13): p_u_34, (ref 14): v_u_16 ]]
            p_u_31._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
            if v_u_38 == nil or v_u_39 == nil then
                return p_u_33:remove_menu(v_u_36);
            else
                local v_u_47 = p_u_31._menus:push_menu(v_u_20:new(p_u_31, p_u_32, p_u_33):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                local function _() --[[ Name: do_combine_song ]] --[[ Line: 199 ]]
                    --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_39, (copy 3): v_u_47, (ref 4): p_u_33, (ref 5): v_u_20, (ref 6): p_u_32, (ref 7): v_u_36, (ref 8): v_u_26, (ref 9): p_u_35 ]]
                    p_u_31._shop_local_protocol:try_combine_song(v_u_39, function(p48, p_u_49, p50) --[[ Line: 200 ]]
                        --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_47, (ref 3): p_u_33, (ref 4): v_u_20, (ref 5): p_u_32, (ref 6): v_u_36, (ref 7): v_u_26, (ref 8): p_u_35 ]]
                        if p48 == true then
                            p_u_31._player_blob_manager:do_sync(function() --[[ Line: 207 ]]
                                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_47, (ref 3): v_u_36, (ref 4): p_u_33, (ref 5): v_u_26, (ref 6): p_u_32, (copy 7): p_u_49, (ref 8): p_u_35 ]]
                                p_u_31._menus:remove_menu(v_u_47)
                                p_u_31._menus:remove_menu(v_u_36)
                                p_u_33:push_menu(v_u_26:new(p_u_31, p_u_32, p_u_33, p_u_49))
                                if p_u_35 then
                                    p_u_35()
                                end;
                            end)
                        else
                            p_u_31._menus:remove_menu(v_u_47)
                            p_u_33:push_menu(v_u_20:new(p_u_31, p_u_32, p_u_33):set_text("Failed", p50))
                        end;
                    end)
                end;
                local v51 = f_get_craft_amount()
                if v51 > 0 then
                    p_u_31._shop_local_protocol:try_craft_song_recipe(v_u_38, function(p52, p53) --[[ Line: 218 ]]
                        --[[ Upvalues: (ref 1): p_u_31, (copy 2): v_u_47, (ref 3): p_u_33, (ref 4): v_u_20, (ref 5): p_u_32, (ref 6): v_u_15, (ref 7): p_u_34, (ref 8): v_u_16, (ref 9): v_u_39, (ref 10): v_u_36, (ref 11): v_u_26, (ref 12): p_u_35 ]]
                        if p52 == true then
                            p_u_31._player_blob_manager:do_sync(function() --[[ Line: 224 ]]
                                --[[ Upvalues: (ref 1): v_u_15, (ref 2): p_u_34, (ref 3): v_u_16, (ref 4): p_u_31, (ref 5): v_u_39, (ref 6): v_u_47, (ref 7): p_u_33, (ref 8): v_u_20, (ref 9): p_u_32, (ref 10): v_u_36, (ref 11): v_u_26, (ref 12): p_u_35 ]]
                                if v_u_15:singleton():key_get_audiomod(p_u_34) == v_u_16.Hard then
                                    p_u_31._shop_local_protocol:try_combine_song(v_u_39, function(p54, p_u_55, p56) --[[ Line: 200 ]]
                                        --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_47, (ref 3): p_u_33, (ref 4): v_u_20, (ref 5): p_u_32, (ref 6): v_u_36, (ref 7): v_u_26, (ref 8): p_u_35 ]]
                                        if p54 == true then
                                            p_u_31._player_blob_manager:do_sync(function() --[[ Line: 207 ]]
                                                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_47, (ref 3): v_u_36, (ref 4): p_u_33, (ref 5): v_u_26, (ref 6): p_u_32, (copy 7): p_u_55, (ref 8): p_u_35 ]]
                                                p_u_31._menus:remove_menu(v_u_47)
                                                p_u_31._menus:remove_menu(v_u_36)
                                                p_u_33:push_menu(v_u_26:new(p_u_31, p_u_32, p_u_33, p_u_55))
                                                if p_u_35 then
                                                    p_u_35()
                                                end;
                                            end)
                                        else
                                            p_u_31._menus:remove_menu(v_u_47)
                                            p_u_33:push_menu(v_u_20:new(p_u_31, p_u_32, p_u_33):set_text("Failed", p56))
                                        end;
                                    end)
                                else
                                    p_u_31._menus:remove_menu(v_u_47)
                                    p_u_31._menus:remove_menu(v_u_36)
                                    p_u_33:push_menu(v_u_26:new(p_u_31, p_u_32, p_u_33, v_u_39))
                                    if p_u_35 then
                                        p_u_35()
                                    end;
                                end;
                            end)
                        else
                            p_u_31._menus:remove_menu(v_u_47)
                            p_u_33:push_menu(v_u_20:new(p_u_31, p_u_32, p_u_33):set_text("Failed", p53))
                        end;
                    end, v51)
                elseif v_u_15:singleton():key_get_audiomod(p_u_34) == v_u_16.Hard then
                    p_u_31._shop_local_protocol:try_combine_song(v_u_39, function(p57, p_u_58, p59) --[[ Line: 200 ]]
                        --[[ Upvalues: (ref 1): p_u_31, (copy 2): v_u_47, (ref 3): p_u_33, (ref 4): v_u_20, (ref 5): p_u_32, (ref 6): v_u_36, (ref 7): v_u_26, (ref 8): p_u_35 ]]
                        if p57 == true then
                            p_u_31._player_blob_manager:do_sync(function() --[[ Line: 207 ]]
                                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_47, (ref 3): v_u_36, (ref 4): p_u_33, (ref 5): v_u_26, (ref 6): p_u_32, (copy 7): p_u_58, (ref 8): p_u_35 ]]
                                p_u_31._menus:remove_menu(v_u_47)
                                p_u_31._menus:remove_menu(v_u_36)
                                p_u_33:push_menu(v_u_26:new(p_u_31, p_u_32, p_u_33, p_u_58))
                                if p_u_35 then
                                    p_u_35()
                                end;
                            end)
                        else
                            p_u_31._menus:remove_menu(v_u_47)
                            p_u_33:push_menu(v_u_20:new(p_u_31, p_u_32, p_u_33):set_text("Failed", p59))
                        end;
                    end)
                end;
            end;
        end))
        v_u_6:button_add_enabled_anim(v_u_43, function() --[[ Line: 242 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            return v_u_36:get_alpha();
        end)
        local v_u_60 = v_u_2:new()
        local function f_create_info_to_audiomod_button(p61, p62) --[[ Name: create_info_to_audiomod_button ]] --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): p_u_31, (ref 3): v_u_6, (ref 4): v_u_5, (ref 5): v_u_40, (ref 6): p_u_32, (ref 7): v_u_7, (ref 8): p_u_33, (ref 9): v_u_30, (ref 10): p_u_35, (ref 11): v_u_15, (copy 12): v_u_60 ]]
            local v_u_63 = nil
            v_u_63 = v_u_36:add_cycle_element(p_u_31, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_40.PrimaryPart, p62), p_u_32, function() --[[ Line: 251 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (ref 3): p_u_33, (ref 4): v_u_30, (ref 5): p_u_32, (ref 6): v_u_63, (ref 7): p_u_35 ]]
                p_u_31._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_33:push_menu(v_u_30:new(p_u_31, p_u_32, p_u_33, v_u_63:get_bound_data().TargetSongKey, p_u_35))
            end):set_auto_zoffset_behaviour(true))
            v_u_63:bind_data({
                ["Toggle"] = v_u_6:button_bind_anim_toggle(v_u_63, function() --[[ Line: 264 ]]
                    --[[ Upvalues: (ref 1): v_u_36 ]]
                    return v_u_36:get_alpha();
                end),
                ["DifficultyDisplay"] = p62.SurfaceGui.Button.DifficultyDisplay,
                ["TargetSongKey"] = v_u_15:invalid_songkey()
            })
            v_u_63:set_visible(false)
            v_u_60:add(p61, v_u_63)
        end;
        f_create_info_to_audiomod_button(v_u_16.Easy, v_u_40.SongDifficultyButtons.EasyModeButton)
        f_create_info_to_audiomod_button(v_u_16.Normal, v_u_40.SongDifficultyButtons.NormalModeButton)
        f_create_info_to_audiomod_button(v_u_16.Hard, v_u_40.SongDifficultyButtons.HardModeButton)
        local v64 = v_u_15:singleton():key_get_audiomod(p_u_34)
        local v65 = v_u_15:singleton():get_audiomod_to_modes_of_songkey(p_u_34)
        for v66, v67 in v_u_60:key_itr() do
            v67:set_visible(true)
            local l_Toggle_0 = v67:get_bound_data().Toggle
            local l_DifficultyDisplay_0 = v67:get_bound_data().DifficultyDisplay
            if v65:contains(v66) then
                local v68 = v65:get(v66)
                v67:get_bound_data().TargetSongKey = v68
                l_DifficultyDisplay_0.Text = tostring((v_u_15:singleton():get_difficulty_for_key(v68)))
                l_DifficultyDisplay_0.TextColor3 = v_u_15:singleton():get_difficulty_color_for_key(v68)
                local v69 = v_u_30:get_songkey_recipe_id(v68)
                if v_u_15:singleton():get_songkey_should_grant(v68) == true and v69 ~= nil then
                    if v68 == p_u_34 then
                        v67:set_enabled(false)
                        l_Toggle_0:set_toggle(true)
                    elseif v_u_13:can_craft_recipe(v45, v69) then
                        v67:set_enabled(true)
                        l_Toggle_0:set_toggle_off_alpha(0.6)
                        l_Toggle_0:set_toggle(false)
                    else
                        v67:set_enabled(false)
                        l_Toggle_0:set_toggle_off_alpha(0.2)
                        l_Toggle_0:set_toggle(false)
                    end;
                else
                    v67:set_enabled(false)
                    l_Toggle_0:set_toggle_off_alpha(0.2)
                    l_Toggle_0:set_toggle(false)
                end;
                if v64 == v66 then
                    v67:set_scale(1.35)
                    v67:set_passive_anim(true)
                else
                    v67:set_scale(0.85)
                    v67:set_passive_anim(false)
                end;
            else
                v67:get_bound_data().TargetSongKey = v_u_15:invalid_songkey()
                l_DifficultyDisplay_0.Text = "-"
                l_DifficultyDisplay_0.TextColor3 = Color3.new(1, 1, 1)
                v67:set_enabled(false)
                l_Toggle_0:set_toggle_off_alpha(0.25)
                l_Toggle_0:set_toggle(false)
                v67:set_scale(0.85)
            end;
        end;
        v_u_36:update_materials_required_display()
        v_u_36:transition_update_visual(0)
        v_u_36:layout()
    end;
    v_u_36.update_materials_required_display = function(_) --[[ Name: update_materials_required_display ]] --[[ Line: 333 ]]
        --[[ Upvalues: (copy 1): v_u_38, (copy 2): p_u_31, (copy 3): f_get_craft_amount, (ref 4): v_u_9, (copy 5): v_u_42, (ref 6): v_u_13, (ref 7): v_u_43 ]]
        if v_u_38 == nil then
            return;
        end;
        local v70 = p_u_31._player_blob_manager:get_player_blob()
        local v71 = f_get_craft_amount()
        local v72 = v_u_9:singleton():get_song_recipe_requirements_dict(v_u_38)
        local v73 = v72:key_list()
        for v74, v75 in v72:key_itr() do
            v72:add(v74, v75 * v71)
        end;
        for v76 = 1, v_u_42:count() do
            v_u_42:get(v76):set_visible(false)
        end;
        for v77 = 1, v_u_42:count() do
            if v73:count() < v77 then
                break;
            end;
            local v78 = v73:get(v77)
            local v79 = v_u_42:get(v77)
            v79:set_visible(true)
            v79:set_info(v_u_9:singleton():get_material_name(v78), v_u_9:singleton():get_material_icon(v78), v_u_9:singleton():tier_get_color(v_u_9:singleton():get_material_tier(v78)), v_u_13:get_count_of_material(v70, v78), v72:get(v78))
        end;
        v_u_43:set_enabled(v_u_13:can_craft_requirements_dict(v70, v72))
    end;
    v_u_36.on_refocus = function(p80) --[[ Name: on_refocus ]] --[[ Line: 367 ]]
        p80:update_materials_required_display()
    end;
    v_u_36.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 371 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        v_u_40:Destroy()
    end;
    local v_u_81 = 1
    local v_u_82 = 1
    v_u_36.layout = function(p83) --[[ Name: layout ]] --[[ Line: 377 ]]
        --[[ Upvalues: (copy 1): p_u_32, (ref 2): v_u_82, (ref 3): v_u_40, (ref 4): v_u_41 ]]
        p83:opt_rescale_to_max_nxy(p_u_32, 0.8, 0.8, v_u_82)
        local v84, v85 = p83:opt_update_cframe_params(p_u_32, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p83:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v84 == true then
            v_u_40:SetPrimaryPartCFrame(v85)
        end;
        v_u_41:layout()
    end;
    v_u_36.set_alpha = function(_, p86) --[[ Name: set_alpha ]] --[[ Line: 391 ]]
        --[[ Upvalues: (ref 1): v_u_81, (ref 2): v_u_1, (ref 3): v_u_40 ]]
        if v_u_81 ~= p86 then
            v_u_81 = p86
            v_u_1:r_set_alpha(v_u_40, v_u_81)
        end;
    end;
    v_u_36.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 397 ]]
        --[[ Upvalues: (ref 1): v_u_81 ]]
        return v_u_81;
    end;
    v_u_36.set_scale = function(_, p87) --[[ Name: set_scale ]] --[[ Line: 398 ]]
        --[[ Upvalues: (ref 1): v_u_82 ]]
        v_u_82 = p87
    end;
    v_u_36.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 399 ]]
        --[[ Upvalues: (ref 1): v_u_82 ]]
        return v_u_82;
    end;
    v_u_36.get_native_size = function(p88) --[[ Name: get_native_size ]] --[[ Line: 401 ]]
        return p88._native_size;
    end;
    v_u_36.get_size = function(p89) --[[ Name: get_size ]] --[[ Line: 404 ]]
        return p89._size;
    end;
    v_u_36.set_size = function(p90, p91) --[[ Name: set_size ]] --[[ Line: 407 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        p90._size = p91
        v_u_40.PrimaryPart.Size = Vector3.new(p91.X, p91.Y, 0)
    end;
    v_u_36.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 411 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        return v_u_40.PrimaryPart.Position;
    end;
    v_u_36.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 414 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        return v_u_40.PrimaryPart.SurfaceGui;
    end;
    v_u_36.set_showing = function(_, p92) --[[ Name: set_showing ]] --[[ Line: 417 ]]
        --[[ Upvalues: (ref 1): v_u_40, (ref 2): v_u_8 ]]
        if p92 then
            v_u_40.Parent = v_u_8:get_world_ui_folder()
        else
            v_u_40.Parent = nil
        end;
    end;
    f_cons()
    return v_u_36;
end;
return v_u_30;
