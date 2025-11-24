-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:40 PM
-- Time elapsed: 18 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_8 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.LocalShared.ShopLocalProtocol)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.SongShopUIItem)
local v_u_13 = require(game.ReplicatedStorage.Lobby.Menus.SongAcquiredV2UI)
local v_u_14 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_15 = require(game.ReplicatedStorage.Lobby.Dialogue.SongShopDialogue)
local v_u_16 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.SongsAcquiredUI)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.SaleInfo)
local v_u_19 = require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_20 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_21 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_22 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.PreviewGame.PreviewGameStartupMenu)
local v_u_23 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v24 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_25 = nil
local v_u_26 = nil
local v_u_27 = nil
local v_u_28 = nil
v24:require_client(function() --[[ Line: 38 ]]
    --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_26, (ref 3): v_u_27, (ref 4): v_u_28 ]]
    v_u_25 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_26 = require(game.ReplicatedStorage.Lobby.Menus.CraftSongUI)
    v_u_27 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_28 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
end)
local v_u_29 = {
    ["Mode"] = {
        ["Closed"] = 1,
        ["InfoRequest"] = 2,
        ["Ready"] = 3
    },
    ["get_restore_menu_name"] = function(_) --[[ Name: get_restore_menu_name ]] --[[ Line: 55 ]]
        return "SongShopUI";
    end
}
local v_u_30 = 1
v_u_29.new = function(_, p_u_31, p_u_32, p_u_33, p_u_34, p_u_35) --[[ Name: new ]] --[[ Line: 58 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_29, (copy 3): v_u_7, (copy 4): v_u_23, (copy 5): v_u_1, (copy 6): v_u_11, (copy 7): v_u_15, (copy 8): v_u_5, (copy 9): v_u_4, (copy 10): v_u_20, (copy 11): v_u_14, (ref 12): v_u_30, (copy 13): v_u_8, (copy 14): v_u_12, (copy 15): v_u_21, (ref 16): v_u_26, (copy 17): v_u_18, (ref 18): v_u_27, (ref 19): v_u_28, (copy 20): v_u_10, (copy 21): v_u_22, (copy 22): v_u_6, (copy 23): v_u_2, (copy 24): v_u_17, (copy 25): v_u_13, (copy 26): v_u_19, (ref 27): v_u_25, (copy 28): v_u_9, (copy 29): v_u_16 ]]
    local v_u_36 = v_u_3:new(p_u_32, p_u_33)
    v_u_36.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29:get_restore_menu_name();
    end;
    local l__shop_local_protocol_0 = p_u_31._shop_local_protocol
    v_u_36.get_shop_local_protocol = function(_) --[[ Name: get_shop_local_protocol ]] --[[ Line: 63 ]]
        --[[ Upvalues: (copy 1): l__shop_local_protocol_0 ]]
        return l__shop_local_protocol_0;
    end;
    local l_InfoRequest_0 = v_u_29.Mode.InfoRequest
    local function _() --[[ Name: request_response_kill ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_29 ]]
        return l_InfoRequest_0 == v_u_29.Mode.Closed;
    end;
    local v_u_37 = 1
    local v_u_38 = 1
    local v_u_39 = nil
    local v_u_40 = nil
    local v_u_41 = nil
    local v_u_42 = nil
    local v_u_43 = nil
    local v_u_44 = nil
    local v_u_45 = nil
    local v_u_46 = nil
    local v_u_47 = nil
    local v_u_48 = nil
    local v_u_49 = nil
    local v_u_50 = {}
    local v_u_51 = 0
    local v_u_52 = nil
    local v_u_53 = nil
    local v_u_54 = nil
    local v_u_55 = nil
    local v_u_56 = nil
    local v_u_57 = nil
    local v_u_58 = v_u_7:invalid_songkey()
    local v_u_59 = v_u_23:new()
    local function f_load_data(p_u_60) --[[ Name: load_data ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_29, (copy 3): v_u_36, (ref 4): v_u_55, (copy 5): l__shop_local_protocol_0, (ref 6): v_u_51, (copy 7): p_u_31 ]]
        l_InfoRequest_0 = v_u_29.Mode.InfoRequest
        v_u_36:update_ui_mode()
        v_u_36:update_blob_sync()
        v_u_55:set_locked(true)
        l__shop_local_protocol_0:request_shop_info_cached(function(p61) --[[ Line: 104 ]]
            --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_29, (ref 3): v_u_51, (ref 4): p_u_31, (ref 5): v_u_36, (ref 6): v_u_55, (copy 7): p_u_60 ]]
            if l_InfoRequest_0 ~= v_u_29.Mode.Closed then
                l_InfoRequest_0 = v_u_29.Mode.Ready
                v_u_51 = p_u_31._player_blob_manager:get_time_to_next_day_sec()
                v_u_36:update_time_display()
                v_u_36:update_ui_mode()
                v_u_36:load_items_from_request_shop_info(p61)
                v_u_55:set_locked(false)
                if p_u_60 then
                    p_u_60()
                end;
            end;
        end)
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): v_u_48, (ref 2): v_u_1, (ref 3): v_u_11, (copy 4): v_u_36, (ref 5): v_u_57, (copy 6): p_u_31, (ref 7): v_u_55, (ref 8): v_u_15, (ref 9): v_u_49, (ref 10): v_u_53, (ref 11): v_u_54, (ref 12): v_u_52, (ref 13): l_InfoRequest_0, (ref 14): v_u_29, (ref 15): v_u_5, (ref 16): v_u_4, (copy 17): p_u_32, (ref 18): v_u_20, (ref 19): v_u_14, (copy 20): p_u_33, (ref 21): v_u_40, (ref 22): v_u_30, (ref 23): v_u_50, (ref 24): v_u_47, (ref 25): v_u_39, (ref 26): v_u_41, (ref 27): v_u_8, (ref 28): v_u_42, (ref 29): v_u_12, (ref 30): v_u_56, (ref 31): v_u_43, (ref 32): v_u_7, (ref 33): v_u_21, (ref 34): v_u_26, (ref 35): v_u_44, (ref 36): v_u_45, (ref 37): v_u_18, (ref 38): v_u_27, (ref 39): v_u_46, (ref 40): v_u_28, (copy 41): f_load_data ]]
        v_u_48 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.SongShopUI:Clone()
        v_u_48.Name = v_u_1:gen_name(v_u_48.Name)
        v_u_48.Parent = v_u_11:get_world_ui_folder()
        v_u_36._native_size = v_u_48.PrimaryPart.Size
        v_u_36._size = v_u_36._native_size
        v_u_57 = p_u_31._bgm_manager:begin_preview_songkey()
        p_u_31:set_character_random_position_around_anchors_fn(function() --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11:get_lobby_anchors().Shop.SongShop.StandAnchor, v_u_11:get_lobby_anchors().Shop.SongShop.LookAnchor;
        end)
        p_u_31:transition_local_camera_to_anchors_fn(function() --[[ Line: 129 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11:get_lobby_anchors().Shop.SongShop.CameraAnchor, v_u_11:get_lobby_anchors().Shop.SongShop.LookAnchor;
        end)
        v_u_55 = v_u_15:new(p_u_31, v_u_36, v_u_36, v_u_48)
        v_u_49 = v_u_48.PrimaryPart.SurfaceGui.LoadingFrame
        local l_Frame_0 = v_u_48.PrimaryPart.SurfaceGui.Frame
        v_u_53 = l_Frame_0.CoinSection.Display
        v_u_54 = l_Frame_0.StarSection.Display
        v_u_52 = l_Frame_0.TimeSection.Display
        l_InfoRequest_0 = v_u_29.Mode.InfoRequest
        v_u_36:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_36, v_u_48.PrimaryPart, v_u_48.BackButtonSurface), p_u_32, function() --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_20, (ref 3): v_u_14, (ref 4): l_InfoRequest_0, (ref 5): v_u_29, (ref 6): p_u_33, (ref 7): v_u_36 ]]
            p_u_31._npcs:try_get_npc(v_u_20.NPC.NPC_Marie, function(p62) --[[ Line: 148 ]]
                p62:set_visible(true)
            end)
            p_u_31._npcs:try_get_npc(v_u_20.NPC.NPC_Mattie, function(p63) --[[ Line: 151 ]]
                p63:set_visible(true)
            end)
            p_u_31._sfx_manager:play_sfx(v_u_14.SFX_MENU_CLOSE)
            l_InfoRequest_0 = v_u_29.Mode.Closed
            p_u_33:remove_menu(v_u_36)
        end))
        v_u_40 = v_u_36:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_36, v_u_48.PrimaryPart, v_u_48.BottomArrowSurface), p_u_32, function() --[[ Line: 163 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_14, (ref 3): v_u_30, (ref 4): v_u_50, (ref 5): v_u_36, (ref 6): v_u_47 ]]
            p_u_31._sfx_manager:play_sfx(v_u_14.SFX_BUTTONPRESS)
            v_u_30 = v_u_30 + 1
            if v_u_30 > #v_u_50 then
                v_u_30 = 1
            end;
            v_u_36:update_selected_shop_item()
            v_u_47:animate_item_updated()
        end)):set_passive_anim(true)
        v_u_39 = v_u_36:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_36, v_u_48.PrimaryPart, v_u_48.TopArrowSurface), p_u_32, function() --[[ Line: 177 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_14, (ref 3): v_u_30, (ref 4): v_u_50, (ref 5): v_u_36, (ref 6): v_u_47 ]]
            p_u_31._sfx_manager:play_sfx(v_u_14.SFX_BUTTONPRESS)
            v_u_30 = v_u_30 - 1
            if v_u_30 <= 0 then
                v_u_30 = #v_u_50
            end;
            v_u_36:update_selected_shop_item()
            v_u_47:animate_item_updated()
        end))
        v_u_41 = v_u_36:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_36, v_u_48.PrimaryPart, v_u_48.BuyButtonSurface), p_u_32, function() --[[ Line: 191 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_14, (ref 3): v_u_50, (ref 4): v_u_30, (ref 5): v_u_36, (ref 6): v_u_8 ]]
            p_u_31._sfx_manager:play_sfx(v_u_14.SFX_MENU_OPEN_LONG)
            if v_u_30 <= #v_u_50 then
                local v64 = v_u_50[v_u_30]
                v_u_36:buy_saleid(v64.SaleId, v64.SaleComboKey, v64.PriceType, v64.PriceValue)
            else
                v_u_8:warnf("SongShopUI buy invalid item")
            end;
        end)):set_passive_anim(true)
        v_u_42 = v_u_36:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_36, v_u_48.PrimaryPart, v_u_48.PlayButton), p_u_32, function() --[[ Line: 205 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_14, (ref 3): v_u_36 ]]
            p_u_31._sfx_manager:play_sfx(v_u_14.SFX_MENU_OPEN_LONG)
            v_u_36:play_button_pressed()
        end)):set_passive_anim(true)
        v_u_42:set_visible(false)
        v_u_47 = v_u_12:new(p_u_31, v_u_48.ShopItemSurface, v_u_36, v_u_48.PrimaryPart)
        v_u_56 = v_u_36:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_47:get_uichild(), v_u_47:get_uichild():get_child_part(), v_u_48.SaleInfoButton), p_u_32, function() --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_14, (ref 3): v_u_36 ]]
            p_u_31._sfx_manager:play_sfx(v_u_14.SFX_MENU_OPEN_LONG)
            v_u_36:sale_info_button_pressed()
        end))
        v_u_56:set_visible(false)
        v_u_43 = v_u_36:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_47:get_uichild(), v_u_47:get_uichild():get_child_part(), v_u_48.NormalOwnedButton), p_u_32, function() --[[ Line: 226 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_14, (ref 3): v_u_36, (ref 4): v_u_7, (ref 5): v_u_21, (ref 6): v_u_26 ]]
            p_u_31._sfx_manager:play_sfx(v_u_14.SFX_MENU_OPEN_LONG)
            local v65 = v_u_36:get_displayed_songkey()
            if v_u_7:singleton():contains_key(v65) then
                local v66 = v_u_7:singleton():get_audiomod_to_modes_of_songkey(v65)
                if v66:contains(v_u_21.Normal) then
                    p_u_31._menus:push_menu(v_u_26:new(p_u_31, p_u_31._spui, p_u_31._menus, v66:get(v_u_21.Normal)))
                end;
            end;
        end))
        v_u_43:set_auto_zoffset_behaviour(true)
        v_u_43:set_visible(false)
        v_u_5:button_add_enabled_anim(v_u_43, function() --[[ Line: 239 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            return v_u_36:get_alpha();
        end)
        v_u_44 = v_u_36:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_47:get_uichild(), v_u_47:get_uichild():get_child_part(), v_u_48.HardOwnedButton), p_u_32, function() --[[ Line: 244 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_14, (ref 3): v_u_36, (ref 4): v_u_7, (ref 5): v_u_21, (ref 6): v_u_26 ]]
            p_u_31._sfx_manager:play_sfx(v_u_14.SFX_MENU_OPEN_LONG)
            local v67 = v_u_36:get_displayed_songkey()
            if v_u_7:singleton():contains_key(v67) then
                local v68 = v_u_7:singleton():get_audiomod_to_modes_of_songkey(v67)
                if v68:contains(v_u_21.Hard) then
                    p_u_31._menus:push_menu(v_u_26:new(p_u_31, p_u_31._spui, p_u_31._menus, v68:get(v_u_21.Hard)))
                end;
            end;
        end))
        v_u_44:set_auto_zoffset_behaviour(true)
        v_u_44:set_visible(false)
        v_u_5:button_add_enabled_anim(v_u_44, function() --[[ Line: 257 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            return v_u_36:get_alpha();
        end)
        v_u_45 = v_u_36:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_47:get_uichild(), v_u_47:get_uichild():get_child_part(), v_u_48.PreviewButton), p_u_32, function() --[[ Line: 262 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_14, (ref 3): v_u_47, (ref 4): v_u_18, (ref 5): v_u_27, (ref 6): v_u_7, (ref 7): v_u_36 ]]
            p_u_31._sfx_manager:play_sfx(v_u_14.SFX_MENU_OPEN_LONG)
            if v_u_47:selected_item_is_sale() then
                local v_u_69 = v_u_18:get_songids_for_saleid((v_u_47:selected_item_sale_id()))
                p_u_31._menus:push_menu(v_u_27:new(p_u_31, p_u_31._spui, p_u_31._menus, function(p70) --[[ Line: 268 ]]
                    --[[ Upvalues: (copy 1): v_u_69 ]]
                    p70:set_header_text("Select Song")
                    p70:get_element_list():push_back_from_list(v_u_69)
                end, function(p71, p72, p73, _, p74) --[[ Line: 272 ]]
                    --[[ Upvalues: (ref 1): v_u_7 ]]
                    if v_u_7:singleton():contains_key(p71) then
                        p72.Text = v_u_7:singleton():get_title_for_key(p71)
                        p73.Image = v_u_7:singleton():get_coverimage_assetid_for_key(p71)
                        p74:get_description_display().Text = string.format("Difficulty: %d", v_u_7:singleton():get_difficulty_for_key(p71))
                        p74:set_select_button_text("Preview")
                    end;
                end, function(p75) --[[ Line: 281 ]]
                    --[[ Upvalues: (ref 1): v_u_7, (ref 2): p_u_31 ]]
                    if p75 and v_u_7:singleton():contains_key(p75) then
                        p_u_31._game_join:set_last_loaded_songkey(p75)
                        p_u_31._spectate_manager:start_preview_game()
                    end;
                end))
            else
                local v76 = v_u_36:get_displayed_songkey()
                if v_u_7:singleton():contains_key(v76) then
                    p_u_31._game_join:set_last_loaded_songkey(v76)
                    p_u_31._spectate_manager:start_preview_game()
                end;
            end;
        end))
        v_u_46 = v_u_36:add_cycle_element(p_u_31, 1, v_u_5:new(v_u_4:new(v_u_47:get_uichild(), v_u_47:get_uichild():get_child_part(), v_u_48.InfoButtonSurface), p_u_32, function() --[[ Line: 302 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_7, (ref 3): v_u_28, (ref 4): p_u_31 ]]
            local v77 = v_u_36:get_displayed_songkey()
            if v_u_7:singleton():contains_key(v77) then
                v_u_28:show_song_info_popup(p_u_31, v77)
            end;
        end))
        f_load_data()
        p_u_31._npcs:try_get_npc(v_u_20.NPC.NPC_Marie, function(p78) --[[ Line: 312 ]]
            p78:set_visible(false)
        end)
        p_u_31._npcs:try_get_npc(v_u_20.NPC.NPC_Mattie, function(p79) --[[ Line: 315 ]]
            p79:set_visible(false)
        end)
    end;
    local function _(p80) --[[ Name: get_player_songkey_owned_count_including_collection ]] --[[ Line: 320 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_31 ]]
        return v_u_10:get_song_key_owned_count_including_collection(p_u_31._player_blob_manager:get_player_blob(), p80, p_u_31._player_blob_manager:get_cached_collection_info());
    end;
    v_u_36.update_ui_mode = function(_) --[[ Name: update_ui_mode ]] --[[ Line: 324 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_29, (ref 3): v_u_39, (ref 4): v_u_40, (ref 5): v_u_41, (ref 6): v_u_47, (ref 7): v_u_56, (ref 8): v_u_43, (ref 9): v_u_44, (ref 10): v_u_45, (ref 11): v_u_46, (ref 12): v_u_42, (ref 13): v_u_49 ]]
        if l_InfoRequest_0 == v_u_29.Mode.InfoRequest then
            v_u_39:set_visible(false)
            v_u_40:set_visible(false)
            v_u_41:set_visible(false)
            v_u_47:set_visible(false)
            v_u_56:set_visible(false)
            v_u_43:set_visible(false)
            v_u_44:set_visible(false)
            v_u_45:set_visible(false)
            v_u_46:set_visible(false)
            v_u_42:set_visible(false)
            v_u_49.Visible = true
        else
            v_u_39:set_visible(true)
            v_u_40:set_visible(true)
            v_u_41:set_visible(true)
            v_u_47:set_visible(true)
            v_u_43:set_visible(true)
            v_u_44:set_visible(true)
            v_u_45:set_visible(true)
            v_u_46:set_visible(true)
            v_u_49.Visible = false
        end;
    end;
    v_u_36.load_items_from_request_shop_info = function(p81, p82) --[[ Name: load_items_from_request_shop_info ]] --[[ Line: 350 ]]
        --[[ Upvalues: (ref 1): v_u_50, (copy 2): p_u_34, (ref 3): v_u_30, (ref 4): v_u_8 ]]
        v_u_50 = p82.AvailableItems
        if p_u_34 == nil then
            if v_u_30 > #v_u_50 then
                v_u_8:warnf("SongShopUI:load_items_from_request_shop_info _i_shop_available_items > #_shop_available_items")
                v_u_30 = 1
            end;
        elseif p_u_34 <= #v_u_50 and p_u_34 > 0 then
            v_u_30 = p_u_34
        else
            v_u_8:warnf("SongShopUI:load_items_from_request_shop_info _initial_song_shop_page(%s) invalid #_shop_available_items(%d)", tostring(p_u_34), #v_u_50)
            v_u_30 = 1
        end;
        p81:update_selected_shop_item()
    end;
    v_u_36.get_displayed_songkey = function(_) --[[ Name: get_displayed_songkey ]] --[[ Line: 376 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_50, (ref 3): v_u_7 ]]
        if v_u_30 > #v_u_50 then
            return v_u_7:invalid_songkey();
        else
            return v_u_50[v_u_30].SongKey;
        end;
    end;
    v_u_36.update_selected_shop_item = function(p83) --[[ Name: update_selected_shop_item ]] --[[ Line: 381 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_41, (ref 4): v_u_42, (ref 5): v_u_56, (ref 6): v_u_43, (ref 7): v_u_44, (ref 8): v_u_45, (ref 9): v_u_46, (ref 10): v_u_55, (ref 11): v_u_47, (ref 12): v_u_50, (ref 13): v_u_30, (ref 14): v_u_58, (copy 15): p_u_31, (copy 16): v_u_59, (ref 17): v_u_21, (ref 18): v_u_10, (ref 19): v_u_5, (ref 20): v_u_22 ]]
        local v84 = p83:get_displayed_songkey()
        if v_u_7:singleton():contains_key(v84) == true then
            v_u_55:song_selected(v84)
            v_u_47:set_item_info(v_u_50[v_u_30])
            local v85 = v_u_47:can_purchase()
            v_u_41:set_visible(v85)
            if v85 == true then
                v_u_42:set_visible(false)
            elseif v_u_47:selected_item_is_sale() then
                v_u_42:set_visible(false)
            else
                v_u_42:set_visible(true)
            end;
            local v86 = v_u_47:get_preview_songkey()
            if v_u_7:singleton():contains_key(v86) then
                v_u_58 = v86
                if p_u_31._bgm_manager:get_preview_songkey() == v_u_7:invalid_songkey() then
                    p_u_31._bgm_manager:preview_songkey(v_u_58)
                end;
                v_u_59:add_cooldown(0.5)
                if v_u_7:singleton():contains_key(v_u_58) then
                    p_u_31._game_join:set_last_loaded_songkey(v_u_58)
                end;
            end;
            local v87 = p_u_31._player_blob_manager:get_player_blob()
            if v_u_47:selected_item_is_sale() then
                v_u_56:set_visible(true)
                v_u_43:set_visible(false)
                v_u_44:set_visible(false)
                v_u_45:set_visible(true)
                v_u_46:set_visible(false)
            else
                v_u_56:set_visible(false)
                local v88 = v_u_7:singleton():get_audiomod_to_modes_of_songkey(v84)
                if v88:contains(v_u_21.Normal) and v88:contains(v_u_21.Hard) then
                    v_u_43:set_visible(true)
                    v_u_44:set_visible(true)
                    v_u_45:set_visible(true)
                    local v89 = v88:get(v_u_21.Normal)
                    if v_u_10:get_song_key_owned_count_including_collection(p_u_31._player_blob_manager:get_player_blob(), v89, p_u_31._player_blob_manager:get_cached_collection_info()) > 0 then
                        v_u_5:set_button_text(v_u_43, string.format("%s: <font color=\"%s\">%s</font>", v_u_21:mod_to_name(v_u_21.Normal), "#FFFFFF", "Owned"))
                    else
                        v_u_5:set_button_text(v_u_43, string.format("%s: <font color=\"%s\">%s</font>", v_u_21:mod_to_name(v_u_21.Normal), "#BBBBBB", "Not Owned"))
                    end;
                    if v_u_22:can_craft_songkey(v87, v89, p_u_31._player_blob_manager:get_cached_collection_info()) then
                        v_u_43:set_enabled(true)
                    else
                        v_u_43:set_enabled(false)
                    end;
                    if v_u_10:get_song_key_owned_count_including_collection(p_u_31._player_blob_manager:get_player_blob(), v88:get(v_u_21.Hard), p_u_31._player_blob_manager:get_cached_collection_info()) > 0 then
                        v_u_5:set_button_text(v_u_44, string.format("%s: <font color=\"%s\">%s</font>", v_u_21:mod_to_name(v_u_21.Hard), "#FFFFFF", "Owned"))
                    else
                        v_u_5:set_button_text(v_u_44, string.format("%s: <font color=\"%s\">%s</font>", v_u_21:mod_to_name(v_u_21.Hard), "#BBBBBB", "Not Owned"))
                    end;
                    if v_u_22:can_craft_songkey(v87, v89, p_u_31._player_blob_manager:get_cached_collection_info()) then
                        v_u_44:set_enabled(true)
                    else
                        v_u_44:set_enabled(false)
                    end;
                else
                    v_u_43:set_visible(false)
                    v_u_44:set_visible(false)
                    v_u_45:set_visible(false)
                end;
                v_u_46:set_visible(true)
            end;
        else
            v_u_8:warnf("SongShopUI:update_selected_shop_item() no available items")
            v_u_41:set_visible(false)
            v_u_42:set_visible(false)
            v_u_56:set_visible(false)
            v_u_43:set_visible(false)
            v_u_44:set_visible(false)
            v_u_45:set_visible(false)
            v_u_46:set_visible(false)
            return;
        end;
    end;
    local v_u_90 = v_u_7:invalid_songkey()
    v_u_36.buy_saleid = function(_, p_u_91, p_u_92, p93, p94) --[[ Name: buy_saleid ]] --[[ Line: 484 ]]
        --[[ Upvalues: (copy 1): p_u_33, (ref 2): v_u_6, (copy 3): p_u_31, (copy 4): p_u_32, (copy 5): l__shop_local_protocol_0, (ref 6): v_u_41, (ref 7): v_u_18, (ref 8): v_u_2, (ref 9): v_u_10, (ref 10): v_u_17, (ref 11): v_u_13, (ref 12): p_u_35, (ref 13): v_u_90, (ref 14): v_u_19 ]]
        local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 485 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_6, (ref 3): p_u_31, (ref 4): p_u_32, (ref 5): l__shop_local_protocol_0, (copy 6): p_u_91, (ref 7): v_u_41, (copy 8): p_u_92, (ref 9): v_u_18, (ref 10): v_u_2, (ref 11): v_u_10, (ref 12): v_u_17, (ref 13): v_u_13, (ref 14): p_u_35, (ref 15): v_u_90 ]]
            local v_u_95 = p_u_33:push_menu(v_u_6:new(p_u_31, p_u_32, p_u_33):set_text("Purchasing...", "Please wait..."):set_close_button_visible(false))
            l__shop_local_protocol_0:try_purchase_saleitem(p_u_91, function(p96, p97, p_u_98) --[[ Line: 488 ]]
                --[[ Upvalues: (ref 1): v_u_41, (ref 2): p_u_33, (copy 3): v_u_95, (ref 4): v_u_6, (ref 5): p_u_31, (ref 6): p_u_32, (ref 7): p_u_92, (ref 8): v_u_18, (ref 9): v_u_2, (ref 10): v_u_10, (ref 11): v_u_17, (ref 12): v_u_13, (ref 13): p_u_35, (ref 14): v_u_90 ]]
                v_u_41:set_visible(false)
                if p96 == false then
                    p_u_33:remove_menu(v_u_95)
                    p_u_33:push_menu(v_u_6:new(p_u_31, p_u_32, p_u_33):set_text("Purchase Failed", p97))
                else
                    local v_u_99 = {}
                    if p_u_92 == nil then
                        table.insert(v_u_99, 1, p_u_98)
                    else
                        v_u_99 = v_u_18:get_songids_for_saleid(p_u_92):table_copy()
                    end;
                    p_u_31._player_blob_manager:get_player_blob()
                    local v_u_100 = v_u_2:new()
                    for v101 = 1, #v_u_99 do
                        local v102 = v_u_99[v101]
                        if v_u_10:get_song_key_owned_count_including_collection(p_u_31._player_blob_manager:get_player_blob(), v102, p_u_31._player_blob_manager:get_cached_collection_info()) == 0 then
                            p_u_31._player_blob_manager:add_recently_acquired_songid(v102)
                            v_u_100:add(v102, true)
                        end;
                    end;
                    p_u_31._player_blob_manager:do_sync(function(_) --[[ Line: 513 ]]
                        --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_95, (ref 3): p_u_92, (ref 4): v_u_17, (ref 5): p_u_31, (ref 6): p_u_32, (ref 7): v_u_99, (copy 8): v_u_100, (ref 9): v_u_13, (copy 10): p_u_98, (ref 11): p_u_35, (ref 12): v_u_90 ]]
                        p_u_33:remove_menu(v_u_95)
                        if p_u_92 == nil then
                            p_u_33:push_menu(v_u_13:new(p_u_31, p_u_32, p_u_33, p_u_98))
                            if p_u_35 then
                                p_u_35(p_u_98)
                                p_u_35 = nil
                            end;
                        else
                            p_u_33:push_menu(v_u_17:new(p_u_31, p_u_32, p_u_33, v_u_99, v_u_100))
                        end;
                        v_u_90 = p_u_98
                    end)
                end;
            end)
        end;
        local v103 = v_u_19:playerblob_purchase_needs_redirect(p_u_31._player_blob_manager:get_player_blob(), p93, p94)
        if v103:is_valid() then
            v_u_19:show_purchase_redirect(p_u_31, v103, function(p104) --[[ Line: 534 ]]
                --[[ Upvalues: (copy 1): f_do_purchase ]]
                if p104 then
                    f_do_purchase()
                end;
            end)
        else
            f_do_purchase()
        end;
    end;
    v_u_36.play_button_pressed = function(p105) --[[ Name: play_button_pressed ]] --[[ Line: 544 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_31, (ref 3): v_u_25 ]]
        local v106 = p105:get_displayed_songkey()
        if v_u_7:singleton():contains_key(v106) then
            p_u_31._menus:push_menu(v_u_25:new(p_u_31, p_u_31._spui, p_u_31._menus, v106, nil))
        end;
    end;
    v_u_36.sale_info_button_pressed = function(_) --[[ Name: sale_info_button_pressed ]] --[[ Line: 554 ]]
        --[[ Upvalues: (ref 1): v_u_47, (ref 2): v_u_18, (copy 3): p_u_31, (ref 4): v_u_10, (ref 5): v_u_7, (copy 6): p_u_33, (ref 7): v_u_6, (copy 8): p_u_32 ]]
        local v107 = v_u_18:get_songids_for_saleid((v_u_47:selected_item_sale_id()))
        p_u_31._player_blob_manager:get_player_blob()
        local v108 = ""
        for v109 = 1, v107:count() do
            local v110 = v107:get(v109)
            v108 = v108 .. string.format("%s (Difficulty: %d) %s\n", v_u_7:singleton():get_title_for_key(v110), v_u_7:singleton():get_difficulty_for_key(v110), v_u_10:get_song_key_owned_count_including_collection(p_u_31._player_blob_manager:get_player_blob(), v110, p_u_31._player_blob_manager:get_cached_collection_info()) > 0 and "(Owned)" or "")
        end;
        p_u_33:push_menu(v_u_6:new(p_u_31, p_u_32, p_u_33):set_text("Sale Info", v108))
    end;
    v_u_36.update_time_display = function(_) --[[ Name: update_time_display ]] --[[ Line: 581 ]]
        --[[ Upvalues: (ref 1): v_u_51, (ref 2): v_u_52, (ref 3): v_u_1 ]]
        if v_u_51 > 0 then
            v_u_52.Text = v_u_1:format_sec_time(v_u_51)
        else
            v_u_52.Text = "-"
        end;
    end;
    v_u_36.on_refocus = function(_) --[[ Name: on_refocus ]] --[[ Line: 589 ]]
        --[[ Upvalues: (copy 1): f_load_data, (ref 2): v_u_90, (ref 3): v_u_7, (ref 4): v_u_55 ]]
        f_load_data(function() --[[ Line: 590 ]]
            --[[ Upvalues: (ref 1): v_u_90, (ref 2): v_u_7, (ref 3): v_u_55 ]]
            if v_u_90 ~= v_u_7:invalid_songkey() then
                v_u_55:song_purchased(v_u_90)
                v_u_90 = v_u_7:invalid_songkey()
            end;
        end)
    end;
    v_u_36.behaviour_update = function(p111, p112, p113) --[[ Name: behaviour_update ]] --[[ Line: 598 ]]
        --[[ Upvalues: (ref 1): v_u_47, (ref 2): v_u_51, (ref 3): v_u_9, (ref 4): v_u_16, (ref 5): v_u_55, (copy 6): v_u_59, (ref 7): v_u_7, (ref 8): v_u_58, (copy 9): p_u_31 ]]
        p111:behaviour_update_base(p112, p113)
        p111:update_blob_sync()
        v_u_47:behaviour_update(p112, p113)
        v_u_51 = math.max(v_u_51 - v_u_9:TimescaleToDeltaTime(p112), 0)
        p111:update_time_display()
        if p111._current_mode == v_u_16.MODE_OPEN then
            v_u_55:update(p112)
            v_u_59:update(p112)
            if v_u_59:is_on_cooldown() ~= true and (v_u_7:singleton():contains_key(v_u_58) and v_u_58 ~= p_u_31._bgm_manager:get_preview_songkey()) then
                p_u_31._bgm_manager:preview_songkey(v_u_58)
                v_u_59:add_cooldown(0.5)
            end;
        end;
        p113._player_blob_manager:test_time_to_next_day_and_update()
    end;
    local v_u_114 = -1
    v_u_36.update_blob_sync = function(_) --[[ Name: update_blob_sync ]] --[[ Line: 622 ]]
        --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_114, (ref 3): v_u_53, (ref 4): v_u_1, (ref 5): v_u_10, (ref 6): v_u_54, (ref 7): v_u_47 ]]
        if p_u_31._player_blob_manager:is_synced() and p_u_31._player_blob_manager:get_synced_time() ~= v_u_114 then
            v_u_114 = p_u_31._player_blob_manager:get_synced_time()
            local v115 = p_u_31._player_blob_manager:get_player_blob()
            v_u_53.Text = v_u_1:comma_value(v_u_10:get_coin_currency(v115))
            v_u_54.Text = v_u_1:comma_value(v_u_10:get_star_currency(v115))
            v_u_47:player_blob_updated()
        end;
    end;
    v_u_36.visual_update = function(p116, p117, p118) --[[ Name: visual_update ]] --[[ Line: 633 ]]
        --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_47 ]]
        if p_u_31:transition_local_camera_cframe_finished() ~= false then
            p116:visual_update_base(p117, p118)
            v_u_47:visual_update(p117, p118)
        end;
    end;
    v_u_36.layout = function(p119) --[[ Name: layout ]] --[[ Line: 642 ]]
        --[[ Upvalues: (copy 1): p_u_32, (ref 2): v_u_38, (ref 3): v_u_48, (ref 4): v_u_55 ]]
        p_u_32:uiobj_rescale_to_max_nxy(p119, 0.6, 0.85, v_u_38)
        v_u_48:SetPrimaryPartCFrame(p_u_32:get_cframe({
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p119:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
        v_u_55:layout()
    end;
    v_u_36.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 652 ]]
        --[[ Upvalues: (ref 1): v_u_48, (copy 2): p_u_31, (ref 3): v_u_20, (ref 4): v_u_57 ]]
        v_u_48:Destroy()
        p_u_31._npcs:try_get_npc(v_u_20.NPC.NPC_Marie, function(p120) --[[ Line: 654 ]]
            p120:set_visible(true)
        end)
        p_u_31._npcs:try_get_npc(v_u_20.NPC.NPC_Mattie, function(p121) --[[ Line: 657 ]]
            p121:set_visible(true)
        end)
        p_u_31._bgm_manager:stop_song_preview(v_u_57)
    end;
    v_u_36.set_alpha = function(_, p122) --[[ Name: set_alpha ]] --[[ Line: 663 ]]
        --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_1, (ref 3): v_u_48 ]]
        if v_u_37 ~= p122 then
            v_u_37 = p122
            v_u_1:r_set_alpha(v_u_48, v_u_37)
        end;
    end;
    v_u_36.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 669 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        return v_u_37;
    end;
    v_u_36.set_scale = function(_, p123) --[[ Name: set_scale ]] --[[ Line: 670 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        v_u_38 = p123
    end;
    v_u_36.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 671 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        return v_u_38;
    end;
    v_u_36.get_native_size = function(p124) --[[ Name: get_native_size ]] --[[ Line: 673 ]]
        return p124._native_size;
    end;
    v_u_36.get_size = function(p125) --[[ Name: get_size ]] --[[ Line: 676 ]]
        return p125._size;
    end;
    v_u_36.set_size = function(p126, p127) --[[ Name: set_size ]] --[[ Line: 679 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        p126._size = p127
        v_u_48.PrimaryPart.Size = Vector3.new(p127.X, p127.Y, 0)
    end;
    v_u_36.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 683 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        return v_u_48.PrimaryPart.Position;
    end;
    v_u_36.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 686 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        return v_u_48.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_36;
end;
return v_u_29;
