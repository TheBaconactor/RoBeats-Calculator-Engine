-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:40 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.LocalShared.ShopLocalProtocol)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_11 = require(game.ReplicatedStorage.Lobby.UI.GearShopUIItem)
local v_u_12 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_13 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_14 = require(game.ReplicatedStorage.Lobby.Dialogue.GearShopDialogue)
local v_u_15 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_16 = require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
local v_u_17 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_18 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_19 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
local v_u_20 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_21 = {
    ["Mode"] = {
        ["Closed"] = 1,
        ["InfoRequest"] = 2,
        ["Ready"] = 3
    }
}
v_u_21.new = function(_, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_21, (copy 3): v_u_1, (copy 4): v_u_10, (copy 5): v_u_14, (copy 6): v_u_5, (copy 7): v_u_4, (copy 8): v_u_12, (copy 9): v_u_7, (copy 10): v_u_11, (copy 11): v_u_18, (copy 12): v_u_6, (copy 13): v_u_17, (copy 14): v_u_19, (copy 15): v_u_2, (copy 16): v_u_20, (copy 17): v_u_13, (copy 18): v_u_16, (copy 19): v_u_8, (copy 20): v_u_15, (copy 21): v_u_9 ]]
    local v_u_25 = v_u_3:new(p_u_23, p_u_24)
    local l__shop_local_protocol_0 = p_u_22._shop_local_protocol
    v_u_25.get_shop_local_protocol = function(_) --[[ Name: get_shop_local_protocol ]] --[[ Line: 41 ]]
        --[[ Upvalues: (copy 1): l__shop_local_protocol_0 ]]
        return l__shop_local_protocol_0;
    end;
    local l_InfoRequest_0 = v_u_21.Mode.InfoRequest
    local function _() --[[ Name: request_response_kill ]] --[[ Line: 44 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_21 ]]
        return l_InfoRequest_0 == v_u_21.Mode.Closed;
    end;
    local v_u_26 = 1
    local v_u_27 = 1
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = 1
    local v_u_35 = {}
    local v_u_36 = 0
    local v_u_37 = nil
    local v_u_38 = nil
    local v_u_39 = nil
    local v_u_40 = nil
    local function f_load_data() --[[ Name: load_data ]] --[[ Line: 69 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_21, (copy 3): v_u_25, (ref 4): v_u_40, (copy 5): l__shop_local_protocol_0, (ref 6): v_u_36, (copy 7): p_u_22 ]]
        l_InfoRequest_0 = v_u_21.Mode.InfoRequest
        v_u_25:update_ui_mode()
        v_u_25:update_blob_sync()
        v_u_40:set_locked(true)
        l__shop_local_protocol_0:request_gear_shop_info_cached(function(p41) --[[ Line: 75 ]]
            --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_21, (ref 3): v_u_36, (ref 4): p_u_22, (ref 5): v_u_25, (ref 6): v_u_40 ]]
            if l_InfoRequest_0 ~= v_u_21.Mode.Closed then
                l_InfoRequest_0 = v_u_21.Mode.Ready
                v_u_36 = p_u_22._player_blob_manager:get_time_to_next_day_sec()
                v_u_25:update_time_display()
                v_u_25:update_ui_mode()
                v_u_25:load_items_from_request_shop_info(p41)
                v_u_40:set_locked(false)
            end;
        end)
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 86 ]]
        --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_1, (ref 3): v_u_10, (copy 4): v_u_25, (ref 5): v_u_37, (ref 6): v_u_38, (ref 7): v_u_39, (ref 8): v_u_40, (ref 9): v_u_14, (copy 10): p_u_22, (ref 11): v_u_33, (ref 12): l_InfoRequest_0, (ref 13): v_u_21, (ref 14): v_u_5, (ref 15): v_u_4, (copy 16): p_u_23, (ref 17): v_u_12, (copy 18): p_u_24, (ref 19): v_u_29, (ref 20): v_u_34, (ref 21): v_u_35, (ref 22): v_u_28, (ref 23): v_u_30, (ref 24): v_u_7, (ref 25): v_u_31, (ref 26): v_u_11, (copy 27): f_load_data, (ref 28): v_u_18 ]]
        v_u_32 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.GearShopV2UI:Clone()
        v_u_32.Name = v_u_1:gen_name(v_u_32.Name)
        v_u_32.Parent = v_u_10:get_world_ui_folder()
        v_u_25._native_size = v_u_32.PrimaryPart.Size
        v_u_25._size = v_u_25._native_size
        v_u_37 = v_u_32.PrimaryPart.SurfaceGui.Frame.CoinSection.Display
        v_u_38 = v_u_32.PrimaryPart.SurfaceGui.Frame.StarSection.Display
        v_u_39 = v_u_32.PrimaryPart.SurfaceGui.Frame.TimeSection.Display
        v_u_40 = v_u_14:new(p_u_22, v_u_25, v_u_25, v_u_32)
        p_u_22:set_character_random_position_around_anchors_fn(function() --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10:get_lobby_anchors().GearShop.Main.StandAnchor, v_u_10:get_lobby_anchors().GearShop.Main.LookAnchor;
        end)
        p_u_22:transition_local_camera_to_anchors_fn(function() --[[ Line: 103 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10:get_lobby_anchors().GearShop.Main.CameraAnchor, v_u_10:get_lobby_anchors().GearShop.Main.LookAnchor;
        end)
        v_u_33 = v_u_32.PrimaryPart.SurfaceGui.LoadingFrame
        l_InfoRequest_0 = v_u_21.Mode.InfoRequest
        v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_32.PrimaryPart, v_u_32.BackButtonSurface), p_u_23, function() --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_12, (ref 3): l_InfoRequest_0, (ref 4): v_u_21, (ref 5): p_u_24, (ref 6): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_12.SFX_MENU_CLOSE)
            l_InfoRequest_0 = v_u_21.Mode.Closed
            p_u_24:remove_menu(v_u_25)
        end))
        v_u_29 = v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_32.PrimaryPart, v_u_32.BottomArrowSurface), p_u_23, function() --[[ Line: 124 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_12, (ref 3): v_u_34, (ref 4): v_u_35, (ref 5): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_12.SFX_BUTTONPRESS)
            v_u_34 = v_u_34 + 1
            if v_u_34 > #v_u_35 then
                v_u_34 = 1
            end;
            v_u_25:update_selected_shop_item()
        end)):set_passive_anim(true)
        v_u_28 = v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_32.PrimaryPart, v_u_32.TopArrowSurface), p_u_23, function() --[[ Line: 137 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_12, (ref 3): v_u_34, (ref 4): v_u_35, (ref 5): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_12.SFX_BUTTONPRESS)
            v_u_34 = v_u_34 - 1
            if v_u_34 <= 0 then
                v_u_34 = #v_u_35
            end;
            v_u_25:update_selected_shop_item()
        end))
        v_u_30 = v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_32.PrimaryPart, v_u_32.BuyButtonSurface), p_u_23, function() --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_12, (ref 3): v_u_35, (ref 4): v_u_34, (ref 5): v_u_25, (ref 6): v_u_7 ]]
            p_u_22._sfx_manager:play_sfx(v_u_12.SFX_MENU_OPEN_LONG)
            if v_u_34 <= #v_u_35 then
                local v42 = v_u_35[v_u_34]
                v_u_25:buy_saleid(v42.SaleId, v42.PriceType, v42.PriceValue)
            else
                v_u_7:warnf("GearShopUI buy invalid item")
            end;
        end)):set_passive_anim(true)
        v_u_31 = v_u_11:new(p_u_22, v_u_32.ShopItemSurface, v_u_25, v_u_32.PrimaryPart)
        f_load_data()
        p_u_22._npcs:try_get_npc(v_u_18.NPC.NPC_Zara, function(p43) --[[ Line: 165 ]]
            p43:set_visible(false)
        end)
    end;
    v_u_25.update_ui_mode = function(_) --[[ Name: update_ui_mode ]] --[[ Line: 170 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_21, (ref 3): v_u_28, (ref 4): v_u_29, (ref 5): v_u_30, (ref 6): v_u_31, (ref 7): v_u_33 ]]
        if l_InfoRequest_0 == v_u_21.Mode.InfoRequest then
            v_u_28:set_visible(false)
            v_u_29:set_visible(false)
            v_u_30:set_visible(false)
            v_u_31:set_visible(false)
            v_u_33.Visible = true
        else
            v_u_28:set_visible(true)
            v_u_29:set_visible(true)
            v_u_30:set_visible(true)
            v_u_31:set_visible(true)
            v_u_33.Visible = false
        end;
    end;
    v_u_25.load_items_from_request_shop_info = function(p44, p45) --[[ Name: load_items_from_request_shop_info ]] --[[ Line: 186 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        v_u_35 = p45.AvailableItems
        table.sort(v_u_35, function(p46, p47) --[[ Line: 189 ]]
            return p46.SaleId < p47.SaleId;
        end)
        p44:update_selected_shop_item()
    end;
    v_u_25.update_selected_shop_item = function(_) --[[ Name: update_selected_shop_item ]] --[[ Line: 196 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_7, (ref 3): v_u_30, (ref 4): v_u_34, (ref 5): v_u_31 ]]
        if #v_u_35 == 0 then
            v_u_7:warnf("GearShopUI:update_selected_shop_item() no available items")
            v_u_30:set_visible(false)
            return;
        elseif v_u_34 <= #v_u_35 then
            v_u_31:set_item_info(v_u_35[v_u_34])
            v_u_30:set_visible(v_u_31:can_purchase())
        else
            v_u_7:warnf("GearShopUI:update_selected_shop_item() i(%d) available(%d)", v_u_34, #v_u_35)
        end;
    end;
    v_u_25.buy_saleid = function(p_u_48, p_u_49, p50, p51) --[[ Name: buy_saleid ]] --[[ Line: 212 ]]
        --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_6, (copy 3): p_u_22, (copy 4): p_u_23, (copy 5): l__shop_local_protocol_0, (ref 6): v_u_17, (ref 7): v_u_19, (ref 8): v_u_2, (ref 9): v_u_20, (ref 10): v_u_13, (ref 11): v_u_40, (ref 12): v_u_16 ]]
        local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 213 ]]
            --[[ Upvalues: (ref 1): p_u_24, (ref 2): v_u_6, (ref 3): p_u_22, (ref 4): p_u_23, (ref 5): l__shop_local_protocol_0, (copy 6): p_u_49, (copy 7): p_u_48, (ref 8): v_u_17, (ref 9): v_u_19, (ref 10): v_u_2, (ref 11): v_u_20, (ref 12): v_u_13, (ref 13): v_u_40 ]]
            local v_u_52 = p_u_24:push_menu(v_u_6:new(p_u_22, p_u_23, p_u_24):set_text("Purchasing...", "Please wait..."):set_close_button_visible(false))
            l__shop_local_protocol_0:try_purchase_gear_shop_saleitem(p_u_49, function(p53, p54, p_u_55, p_u_56) --[[ Line: 216 ]]
                --[[ Upvalues: (ref 1): p_u_24, (copy 2): v_u_52, (ref 3): v_u_6, (ref 4): p_u_22, (ref 5): p_u_23, (ref 6): p_u_48, (ref 7): v_u_17, (ref 8): v_u_19, (ref 9): v_u_2, (ref 10): v_u_20, (ref 11): v_u_13, (ref 12): v_u_40 ]]
                if p53 == false then
                    p_u_24:remove_menu(v_u_52)
                    p_u_24:push_menu(v_u_6:new(p_u_22, p_u_23, p_u_24):set_text("Purchase Failed", p54))
                else
                    p_u_22._player_blob_manager:do_sync(function(_) --[[ Line: 223 ]]
                        --[[ Upvalues: (ref 1): p_u_48, (ref 2): p_u_24, (ref 3): v_u_52, (ref 4): v_u_17, (copy 5): p_u_56, (ref 6): p_u_22, (ref 7): v_u_19, (ref 8): v_u_2, (ref 9): v_u_20, (ref 10): v_u_13, (copy 11): p_u_55, (ref 12): v_u_40 ]]
                        p_u_48:update_selected_shop_item()
                        p_u_24:remove_menu(v_u_52)
                        if v_u_17:singleton():contains_material(p_u_56) then
                            p_u_22._menus:push_menu(v_u_19:new(p_u_22, p_u_22._spui, p_u_22._menus, v_u_2:new({ v_u_20.RewardInfo:new(v_u_20.RewardType.CraftingMaterials, 1, p_u_56) })):set_header_text("Bought!"))
                        elseif v_u_13:singleton():get_equipment_for_id(p_u_55) ~= nil then
                            p_u_22._menus:push_menu(v_u_19:new(p_u_22, p_u_22._spui, p_u_22._menus, v_u_2:new({ v_u_20.RewardInfo:new(v_u_20.RewardType.Gear, 1, p_u_55) })):set_header_text("Bought!"))
                        end;
                        v_u_40:item_purchased()
                    end)
                end;
            end)
        end;
        local v57 = v_u_16:playerblob_purchase_needs_redirect(p_u_22._player_blob_manager:get_player_blob(), p50, p51)
        if v57:is_valid() then
            v_u_16:show_purchase_redirect(p_u_22, v57, function(p58) --[[ Line: 247 ]]
                --[[ Upvalues: (copy 1): f_do_purchase ]]
                if p58 then
                    f_do_purchase()
                end;
            end)
        else
            f_do_purchase()
        end;
    end;
    v_u_25.update_time_display = function(_) --[[ Name: update_time_display ]] --[[ Line: 257 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_39, (ref 3): v_u_1 ]]
        if v_u_36 > 0 then
            v_u_39.Text = v_u_1:format_sec_time(v_u_36)
        else
            v_u_39.Text = "-"
        end;
    end;
    v_u_25.behaviour_update = function(p59, p60, p61) --[[ Name: behaviour_update ]] --[[ Line: 265 ]]
        --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_36, (ref 3): v_u_8, (ref 4): v_u_15, (ref 5): v_u_40 ]]
        p59:behaviour_update_base(p60, p61)
        p59:update_blob_sync()
        v_u_31:behaviour_update(p60, p61)
        v_u_36 = math.max(v_u_36 - v_u_8:TimescaleToDeltaTime(p60), 0)
        p59:update_time_display()
        if p59._current_mode == v_u_15.MODE_OPEN then
            v_u_40:update(p60)
        end;
        p61._player_blob_manager:test_time_to_next_day_and_update()
    end;
    v_u_25.on_refocus = function(_) --[[ Name: on_refocus ]] --[[ Line: 279 ]]
        --[[ Upvalues: (copy 1): f_load_data ]]
        f_load_data()
    end;
    local v_u_62 = -1
    v_u_25.update_blob_sync = function(_) --[[ Name: update_blob_sync ]] --[[ Line: 284 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_62, (ref 3): v_u_37, (ref 4): v_u_1, (ref 5): v_u_9, (ref 6): v_u_38, (ref 7): v_u_31 ]]
        if p_u_22._player_blob_manager:is_synced() and p_u_22._player_blob_manager:get_synced_time() ~= v_u_62 then
            v_u_62 = p_u_22._player_blob_manager:get_synced_time()
            local v63 = p_u_22._player_blob_manager:get_player_blob()
            v_u_37.Text = v_u_1:comma_value(v_u_9:get_coin_currency(v63))
            v_u_38.Text = v_u_1:comma_value(v_u_9:get_star_currency(v63))
            v_u_31:player_blob_updated()
        end;
    end;
    v_u_25.visual_update = function(p64, p65, p66) --[[ Name: visual_update ]] --[[ Line: 295 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_31 ]]
        if p_u_22:transition_local_camera_cframe_finished() ~= false then
            p64:visual_update_base(p65, p66)
            v_u_31:visual_update(p65, p66)
        end;
    end;
    v_u_25.layout = function(p67) --[[ Name: layout ]] --[[ Line: 304 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_27, (ref 3): v_u_32, (ref 4): v_u_40 ]]
        p_u_23:uiobj_rescale_to_max_nxy(p67, 0.6, 0.85, v_u_27)
        v_u_32:SetPrimaryPartCFrame(p_u_23:get_cframe({
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p67:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
        v_u_40:layout()
    end;
    v_u_25.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 314 ]]
        --[[ Upvalues: (ref 1): v_u_32, (copy 2): p_u_22, (ref 3): v_u_18 ]]
        v_u_32:Destroy()
        p_u_22._npcs:try_get_npc(v_u_18.NPC.NPC_Zara, function(p68) --[[ Line: 316 ]]
            p68:set_visible(true)
        end)
    end;
    v_u_25.set_alpha = function(_, p69) --[[ Name: set_alpha ]] --[[ Line: 321 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_1, (ref 3): v_u_32 ]]
        if v_u_26 ~= p69 then
            v_u_26 = p69
            v_u_1:r_set_alpha(v_u_32, v_u_26)
        end;
    end;
    v_u_25.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 327 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    v_u_25.set_scale = function(_, p70) --[[ Name: set_scale ]] --[[ Line: 328 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        v_u_27 = p70
    end;
    v_u_25.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 329 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    v_u_25.get_native_size = function(p71) --[[ Name: get_native_size ]] --[[ Line: 331 ]]
        return p71._native_size;
    end;
    v_u_25.get_size = function(p72) --[[ Name: get_size ]] --[[ Line: 334 ]]
        return p72._size;
    end;
    v_u_25.set_size = function(p73, p74) --[[ Name: set_size ]] --[[ Line: 337 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        p73._size = p74
        v_u_32.PrimaryPart.Size = Vector3.new(p74.X, p74.Y, 0)
    end;
    v_u_25.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 341 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        return v_u_32.PrimaryPart.Position;
    end;
    v_u_25.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 344 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        return v_u_32.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_25;
end;
return v_u_21;
