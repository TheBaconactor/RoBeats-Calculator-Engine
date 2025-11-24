-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:38 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIButton)
local v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_10 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_11 = require(game.ReplicatedStorage.Lobby.UI.DanceShopUIItem)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_13 = require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_14 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
local v_u_16 = {
    ["Mode"] = {
        ["Closed"] = 1,
        ["InfoRequest"] = 2,
        ["Ready"] = 3
    }
}
v_u_16.new = function(_, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 32 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_16, (copy 3): v_u_1, (copy 4): v_u_9, (copy 5): v_u_11, (copy 6): v_u_5, (copy 7): v_u_10, (copy 8): v_u_4, (copy 9): v_u_3, (copy 10): v_u_7, (copy 11): v_u_14, (copy 12): v_u_6, (copy 13): v_u_12, (copy 14): v_u_13, (copy 15): v_u_15, (copy 16): v_u_8 ]]
    local v_u_20 = v_u_2:new(p_u_18, p_u_19)
    local v_u_21 = nil
    local l__shop_local_protocol_0 = p_u_17._shop_local_protocol
    local l_InfoRequest_0 = v_u_16.Mode.InfoRequest
    local function _() --[[ Name: request_response_kill ]] --[[ Line: 40 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_16 ]]
        return l_InfoRequest_0 == v_u_16.Mode.Closed;
    end;
    local v_u_22 = 1
    local v_u_23 = 1
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = 0
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = 1
    local v_u_36 = {}
    local function f_cons() --[[ Name: cons ]] --[[ Line: 72 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_9, (copy 4): v_u_20, (ref 5): v_u_34, (ref 6): v_u_11, (copy 7): p_u_17, (ref 8): v_u_33, (ref 9): v_u_5, (copy 10): p_u_18, (ref 11): v_u_10, (ref 12): l_InfoRequest_0, (ref 13): v_u_16, (copy 14): p_u_19, (ref 15): v_u_26, (ref 16): v_u_4, (ref 17): v_u_3, (ref 18): v_u_36, (ref 19): v_u_35, (ref 20): v_u_7, (ref 21): v_u_31, (ref 22): v_u_32, (ref 23): v_u_24, (ref 24): v_u_25, (ref 25): v_u_27, (ref 26): v_u_28, (ref 27): v_u_30, (ref 28): v_u_14, (copy 29): l__shop_local_protocol_0, (ref 30): v_u_29 ]]
        v_u_21 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.DanceShopUI:Clone()
        v_u_21.Name = v_u_1:gen_name(v_u_21.Name)
        v_u_21.Parent = v_u_9:get_world_ui_folder()
        v_u_20._native_size = v_u_21.PrimaryPart.Size
        v_u_20._size = v_u_20._native_size
        v_u_34 = v_u_11:new(p_u_17, v_u_21.ShopItemSurface, v_u_20, v_u_21.PrimaryPart)
        v_u_33 = v_u_5:new(v_u_21.BackButtonSurface, p_u_18, function() --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_10, (ref 3): l_InfoRequest_0, (ref 4): v_u_16, (ref 5): p_u_19, (ref 6): v_u_20 ]]
            p_u_17._sfx_manager:play_sfx(v_u_10.SFX_MENU_CLOSE)
            l_InfoRequest_0 = v_u_16.Mode.Closed
            p_u_19:remove_menu(v_u_20)
        end)
        v_u_33:set_max_nxy(0.2, 0.2)
        v_u_33:set_position_nxy(1, 0)
        v_u_33:set_anchor_rnxy(1, 0)
        v_u_33:set_visible(false)
        v_u_20:add_cycle_element(p_u_17, 1, v_u_33)
        v_u_26 = v_u_20:add_cycle_element(p_u_17, 1, v_u_4:new(v_u_3:new(v_u_20, v_u_21.PrimaryPart, v_u_21.BuyButtonSurface), p_u_18, function() --[[ Line: 104 ]]
            --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_10, (ref 3): v_u_36, (ref 4): v_u_35, (ref 5): v_u_20, (ref 6): v_u_7 ]]
            p_u_17._sfx_manager:play_sfx(v_u_10.SFX_MENU_OPEN_LONG)
            if v_u_35 <= #v_u_36 then
                local v37 = v_u_36[v_u_35]
                v_u_20:buy_saleid(v37.SaleId, v37.PriceType, v37.PriceValue)
            else
                v_u_7:warnf("GearShopUI buy invalid item")
            end;
        end)):set_passive_anim(true)
        v_u_31 = v_u_20:add_cycle_element(p_u_17, 1, v_u_4:new(v_u_3:new(v_u_20, v_u_21.PrimaryPart, v_u_21.TopArrowSurface), p_u_18, function() --[[ Line: 118 ]]
            --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_10, (ref 3): v_u_35, (ref 4): v_u_36, (ref 5): v_u_20 ]]
            p_u_17._sfx_manager:play_sfx(v_u_10.SFX_BUTTONPRESS)
            v_u_35 = v_u_35 - 1
            if v_u_35 <= 0 then
                v_u_35 = #v_u_36
            end;
            v_u_20:update_selected_shop_item()
        end))
        v_u_32 = v_u_20:add_cycle_element(p_u_17, 1, v_u_4:new(v_u_3:new(v_u_20, v_u_21.PrimaryPart, v_u_21.BottomArrowSurface), p_u_18, function() --[[ Line: 131 ]]
            --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_10, (ref 3): v_u_35, (ref 4): v_u_36, (ref 5): v_u_20 ]]
            p_u_17._sfx_manager:play_sfx(v_u_10.SFX_BUTTONPRESS)
            v_u_35 = v_u_35 + 1
            if v_u_35 > #v_u_36 then
                v_u_35 = 1
            end;
            v_u_20:update_selected_shop_item()
        end))
        pcall(function() --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_9 ]]
            p_u_17:set_local_character_cframe(CFrame.new(v_u_9:get_lobby_anchors().DanceShop.StandAnchor.Position, v_u_9:get_lobby_anchors().DanceShop.StandLookAnchor.Position))
            p_u_17:transition_local_camera_cframe(CFrame.new(v_u_9:get_lobby_anchors().DanceShop.CameraAnchor.Position, v_u_9:get_lobby_anchors().DanceShop.LookAnchor.Position))
        end)
        v_u_24 = v_u_21.MainSurface.SurfaceGui.Frame.LoadingFrame
        v_u_25 = v_u_21.MainSurface.SurfaceGui.Frame.LoadedFrame
        v_u_27 = v_u_25.CoinSection.Display
        v_u_28 = v_u_25.StarSection.Display
        v_u_30 = v_u_25.TimeSection.Display
        v_u_20:update_blob_sync()
        l_InfoRequest_0 = v_u_16.Mode.InfoRequest
        v_u_20:update_ui_mode()
        v_u_9:set_lobby_characters_visible(false)
        p_u_17._lobby_join:get_character_manager():set_nametag_alpha_multiplier(0)
        p_u_17._npcs:try_get_npc(v_u_14.NPC.NPC_DanceMachine, function(p38) --[[ Line: 164 ]]
            p38:set_title_visible(false)
            p38:set_screen_visible(true)
        end)
        l__shop_local_protocol_0:request_dance_shop_info(function(p39, p40) --[[ Line: 169 ]]
            --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_16, (ref 3): v_u_36, (ref 4): v_u_29, (ref 5): v_u_20, (ref 6): v_u_35 ]]
            if l_InfoRequest_0 ~= v_u_16.Mode.Closed then
                v_u_36 = p39.AvailableItems
                v_u_29 = p40
                l_InfoRequest_0 = v_u_16.Mode.Ready
                v_u_20:update_time_display()
                v_u_35 = 1
                v_u_20:update_selected_shop_item()
                v_u_20:update_ui_mode()
            end;
        end)
    end;
    v_u_20.buy_saleid = function(p_u_41, p_u_42, p43, p44) --[[ Name: buy_saleid ]] --[[ Line: 181 ]]
        --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_6, (copy 3): p_u_17, (copy 4): p_u_18, (copy 5): l__shop_local_protocol_0, (ref 6): v_u_12, (ref 7): v_u_13 ]]
        local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 182 ]]
            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_6, (ref 3): p_u_17, (ref 4): p_u_18, (ref 5): l__shop_local_protocol_0, (copy 6): p_u_42, (copy 7): p_u_41, (ref 8): v_u_12 ]]
            local v_u_45 = p_u_19:push_menu(v_u_6:new(p_u_17, p_u_18, p_u_19):set_text("Purchasing...", "Please wait..."):set_close_button_visible(false))
            l__shop_local_protocol_0:try_purchase_dance(p_u_42, function(p46, p47, p_u_48) --[[ Line: 184 ]]
                --[[ Upvalues: (ref 1): p_u_19, (copy 2): v_u_45, (ref 3): v_u_6, (ref 4): p_u_17, (ref 5): p_u_18, (ref 6): p_u_41, (ref 7): v_u_12 ]]
                if p46 == false then
                    p_u_19:remove_menu(v_u_45)
                    p_u_19:push_menu(v_u_6:new(p_u_17, p_u_18, p_u_19):set_text("Purchase Failed", p47))
                else
                    p_u_17._player_blob_manager:do_sync(function(_) --[[ Line: 191 ]]
                        --[[ Upvalues: (ref 1): p_u_41, (ref 2): p_u_19, (ref 3): v_u_45, (ref 4): v_u_6, (ref 5): p_u_17, (ref 6): p_u_18, (ref 7): v_u_12, (copy 8): p_u_48 ]]
                        p_u_41:update_selected_shop_item()
                        p_u_19:remove_menu(v_u_45)
                        p_u_19:push_menu(v_u_6:new(p_u_17, p_u_18, p_u_19):set_text("Bought!", string.format("Bought the Dance \"%s\"!", v_u_12:singleton():get_dance_name_for_id(p_u_48))))
                    end)
                end;
            end)
        end;
        local v49 = v_u_13:playerblob_purchase_needs_redirect(p_u_17._player_blob_manager:get_player_blob(), p43, p44)
        if v49:is_valid() then
            v_u_13:show_purchase_redirect(p_u_17, v49, function(p50) --[[ Line: 207 ]]
                --[[ Upvalues: (copy 1): f_do_purchase ]]
                if p50 then
                    f_do_purchase()
                end;
            end)
        else
            f_do_purchase()
        end;
    end;
    v_u_20.update_selected_shop_item = function(_) --[[ Name: update_selected_shop_item ]] --[[ Line: 217 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_7, (ref 3): v_u_26, (ref 4): v_u_35, (ref 5): v_u_34, (ref 6): v_u_1, (copy 7): p_u_17, (ref 8): v_u_9, (ref 9): v_u_12, (ref 10): v_u_14, (ref 11): v_u_15 ]]
        if #v_u_36 == 0 then
            v_u_7:warnf("DanceShopUI:update_selected_shop_item() no available items")
            v_u_26:set_visible(false)
            return;
        elseif v_u_35 <= #v_u_36 then
            local v51 = v_u_36[v_u_35]
            local l_DanceId_0 = v51.DanceId
            v_u_34:set_item_info(v51)
            v_u_26:set_visible(v_u_34:can_purchase())
            v_u_1:ptry(function() --[[ Line: 229 ]]
                --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_9 ]]
                p_u_17:set_local_character_cframe(CFrame.new(v_u_9:get_lobby_anchors().DanceShop.StandAnchor.Position, v_u_9:get_lobby_anchors().DanceShop.StandLookAnchor.Position))
            end)
            v_u_1:spawn(function() --[[ Line: 235 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): l_DanceId_0, (ref 3): p_u_17 ]]
                local v52 = v_u_12:singleton():get_dance_animation_for_id(l_DanceId_0)
                p_u_17._animate_script:play_animation_instance(v52)
                p_u_17._follow_npc_manager:on_local_character_play_animation(v52)
            end)
            p_u_17._npcs:try_get_npc(v_u_14.NPC.NPC_DanceMachine, function(p53) --[[ Line: 240 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): l_DanceId_0, (ref 3): v_u_15 ]]
                p53:get_screen_icon().Image = v_u_12:singleton():get_dance_icon_for_id(l_DanceId_0)
                p53:get_screen_name_display().Text = string.format("[%d] %s", l_DanceId_0, v_u_12:singleton():get_dance_name_for_id(l_DanceId_0))
                p53:get_screen_name_display().TextColor3 = v_u_15:rarity_to_color(v_u_12:singleton():get_dance_rarity_for_id(l_DanceId_0))
            end)
        else
            v_u_7:warnf("DanceShopUI:update_selected_shop_item() i(%d) available(%d)", v_u_35, #v_u_36)
        end;
    end;
    v_u_20.update_ui_mode = function(_) --[[ Name: update_ui_mode ]] --[[ Line: 250 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_16, (ref 3): v_u_24, (ref 4): v_u_25, (ref 5): v_u_26, (ref 6): v_u_31, (ref 7): v_u_32, (ref 8): v_u_34 ]]
        if l_InfoRequest_0 == v_u_16.Mode.InfoRequest then
            v_u_24.Visible = true
            v_u_25.Visible = false
            v_u_26:set_visible(false)
            v_u_31:set_visible(false)
            v_u_32:set_visible(false)
            v_u_34:set_visible(false)
        else
            v_u_24.Visible = false
            v_u_25.Visible = true
            v_u_26:set_visible(true)
            v_u_31:set_visible(true)
            v_u_32:set_visible(true)
            v_u_34:set_visible(true)
        end;
    end;
    local v_u_54 = -1
    v_u_20.update_blob_sync = function(_) --[[ Name: update_blob_sync ]] --[[ Line: 269 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_54, (ref 3): v_u_27, (ref 4): v_u_1, (ref 5): v_u_28 ]]
        if p_u_17._player_blob_manager:is_synced() and p_u_17._player_blob_manager:get_synced_time() ~= v_u_54 then
            v_u_54 = p_u_17._player_blob_manager:get_synced_time()
            local v55 = p_u_17._player_blob_manager:get_player_blob()
            v_u_27.Text = v_u_1:comma_value(v55.CoinCurrency)
            v_u_28.Text = v_u_1:comma_value(v55.StarCurrency)
        end;
    end;
    v_u_20.update_time_display = function(_) --[[ Name: update_time_display ]] --[[ Line: 279 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_1, (ref 3): v_u_29 ]]
        v_u_30.Text = v_u_1:format_sec_time(v_u_29)
    end;
    v_u_20.visual_update = function(p56, p57, p58) --[[ Name: visual_update ]] --[[ Line: 283 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_33, (ref 3): v_u_34 ]]
        if p_u_17:transition_local_camera_cframe_finished() ~= false then
            v_u_33:set_visible(true)
            v_u_34:visual_update(p57, p58)
            p56:visual_update_base(p57, p58)
        end;
    end;
    v_u_20.behaviour_update = function(p59, p60, p61) --[[ Name: behaviour_update ]] --[[ Line: 294 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_8, (ref 3): v_u_34 ]]
        p59:behaviour_update_base(p60, p61)
        p59:update_blob_sync()
        v_u_29 = math.max(v_u_29 - v_u_8:TimescaleToDeltaTime(p60), 0)
        p59:update_time_display()
        v_u_34:behaviour_update(p60, p61)
    end;
    v_u_20.layout = function(p62) --[[ Name: layout ]] --[[ Line: 306 ]]
        --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_23, (ref 3): v_u_21 ]]
        p_u_18:uiobj_rescale_to_max_nxy(p62, 0.35, 0.75, v_u_23)
        v_u_21:SetPrimaryPartCFrame(p_u_18:get_cframe({
            ["PositionNXY"] = Vector2.new(0, 0.535),
            ["OffsetXYZ"] = p62:anchored_offset(-0.05, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
    end;
    v_u_20.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 315 ]]
        --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_17, (ref 3): v_u_21, (ref 4): v_u_14 ]]
        v_u_9:set_lobby_characters_visible(v_u_9:get_show_other_players())
        p_u_17._lobby_join:get_character_manager():set_nametag_alpha_multiplier(1)
        v_u_21:Destroy()
        p_u_17._npcs:try_get_npc(v_u_14.NPC.NPC_DanceMachine, function(p63) --[[ Line: 319 ]]
            p63:set_title_visible(true)
            p63:set_screen_visible(false)
        end)
    end;
    v_u_20.set_alpha = function(_, p64) --[[ Name: set_alpha ]] --[[ Line: 325 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_1, (ref 3): v_u_21 ]]
        if v_u_22 ~= p64 then
            v_u_22 = p64
            v_u_1:r_set_alpha(v_u_21, v_u_22)
        end;
    end;
    v_u_20.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 331 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22;
    end;
    v_u_20.set_scale = function(_, p65) --[[ Name: set_scale ]] --[[ Line: 332 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        v_u_23 = p65
    end;
    v_u_20.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 333 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        return v_u_23;
    end;
    v_u_20.get_native_size = function(p66) --[[ Name: get_native_size ]] --[[ Line: 335 ]]
        return p66._native_size;
    end;
    v_u_20.get_size = function(p67) --[[ Name: get_size ]] --[[ Line: 338 ]]
        return p67._size;
    end;
    v_u_20.set_size = function(p68, p69) --[[ Name: set_size ]] --[[ Line: 341 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        p68._size = p69
        v_u_21.PrimaryPart.Size = Vector3.new(p69.X, p69.Y, 0)
    end;
    v_u_20.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 345 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21.PrimaryPart.Position;
    end;
    v_u_20.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 348 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_20;
end;
return v_u_16;
