-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:42 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_5 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_7 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_8 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_9 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_11 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_12 = require(game.ReplicatedStorage.LocalShared.TradeLocalProtocol)
local v_u_13 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_14 = require(game.ReplicatedStorage.Lobby.UI.ActivePlayerTradeListElement)
local v_u_15 = require(game.ReplicatedStorage.Shared.ActiveTradeOffer)
local v_u_16 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_18 = require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
local v_u_19 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_20 = require(game.ReplicatedStorage.Lobby.UI.CraftingUISearchSection)
local v_u_21 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_22 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
return {
    ["new"] = function(_, p_u_23, p_u_24, p_u_25) --[[ Name: new ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3, (copy 3): v_u_21, (copy 4): v_u_1, (copy 5): v_u_10, (copy 6): v_u_18, (copy 7): v_u_7, (copy 8): v_u_6, (copy 9): v_u_9, (copy 10): v_u_14, (copy 11): v_u_16, (copy 12): v_u_22, (copy 13): v_u_20, (copy 14): v_u_15, (copy 15): v_u_17, (copy 16): v_u_8, (copy 17): v_u_4, (copy 18): v_u_2, (copy 19): v_u_13, (copy 20): v_u_12, (copy 21): v_u_19, (copy 22): v_u_11 ]]
        local v_u_26 = v_u_5:new(p_u_24, p_u_25)
        local l__trade_local_protocol_0 = p_u_23._trade_local_protocol
        local v_u_27 = nil
        local v_u_28 = 1
        local v_u_29 = 1
        local v_u_30 = nil
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = 0
        local v_u_34 = nil
        local v_u_35 = v_u_3:new()
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = nil
        local v_u_39 = nil
        local v_u_40 = v_u_21:new()
        v_u_26.cons = function(p_u_41) --[[ Name: cons ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_1, (ref 3): v_u_10, (ref 4): v_u_34, (ref 5): v_u_37, (ref 6): v_u_38, (ref 7): v_u_39, (ref 8): v_u_36, (ref 9): v_u_18, (copy 10): p_u_23, (copy 11): p_u_24, (ref 12): v_u_7, (ref 13): v_u_6, (copy 14): l__trade_local_protocol_0, (copy 15): p_u_25, (ref 16): v_u_9, (ref 17): v_u_30, (ref 18): v_u_31, (ref 19): v_u_32 ]]
            v_u_27 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.ActivePlayerTradeUI:Clone()
            v_u_27.Name = v_u_1:gen_name(v_u_27.Name)
            v_u_27.Parent = v_u_10:get_world_ui_folder()
            p_u_41._native_size = v_u_27.PrimaryPart.Size
            p_u_41._size = p_u_41._native_size
            local l_Frame_0 = v_u_27.PrimaryPart.SurfaceGui.Frame
            v_u_34 = l_Frame_0.InventorySection.CoinSection.Display
            v_u_37 = l_Frame_0.PlayerOfferSection.Title
            v_u_38 = l_Frame_0.TargetOfferSection.Title
            v_u_39 = l_Frame_0.TargetOfferSection.CoinSection.Display
            v_u_36 = v_u_18:new(p_u_23, l_Frame_0.PlayerOfferSection.CoinSection.Display, nil, p_u_41, p_u_24):set_empty_message("0"):set_send_behaviour_enabled(false):enforce_numeric(true, function(p42) --[[ Line: 78 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1:clamp(math.floor(p42), 0, 1000000);
            end):enforce_numeric_integer(true)
            p_u_41:add_cycle_element(p_u_23, 1, v_u_7:new(v_u_6:new(p_u_41, v_u_27.PrimaryPart, v_u_27.BackButtonSurface), p_u_24, function() --[[ Line: 85 ]]
                --[[ Upvalues: (ref 1): l__trade_local_protocol_0, (ref 2): p_u_25, (copy 3): p_u_41, (ref 4): p_u_23, (ref 5): v_u_9 ]]
                l__trade_local_protocol_0:trade_leave()
                l__trade_local_protocol_0:stop()
                p_u_25:remove_menu(p_u_41)
                p_u_23._sfx_manager:play_sfx(v_u_9.SFX_MENU_CLOSE)
            end))
            v_u_30 = p_u_41:add_cycle_element(p_u_23, 1, v_u_7:new(v_u_6:new(p_u_41, v_u_27.PrimaryPart, v_u_27.TopArrowSurface), p_u_24, function() --[[ Line: 96 ]]
                --[[ Upvalues: (copy 1): p_u_41, (ref 2): p_u_23, (ref 3): v_u_9 ]]
                p_u_41:inventory_offset_page(-1)
                p_u_23._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
            end))
            v_u_31 = p_u_41:add_cycle_element(p_u_23, 1, v_u_7:new(v_u_6:new(p_u_41, v_u_27.PrimaryPart, v_u_27.BottomArrowSurface), p_u_24, function() --[[ Line: 105 ]]
                --[[ Upvalues: (copy 1): p_u_41, (ref 2): p_u_23, (ref 3): v_u_9 ]]
                p_u_41:inventory_offset_page(1)
                p_u_23._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
            end))
            v_u_32 = p_u_41:add_cycle_element(p_u_23, 1, v_u_7:new(v_u_6:new(p_u_41, v_u_27.PrimaryPart, v_u_27.AcceptButtonSurface), p_u_24, function() --[[ Line: 114 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_9, (copy 3): p_u_41 ]]
                p_u_23._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN)
                p_u_41:accept_pressed()
            end))
            p_u_41:setup_list_elements()
            p_u_41:update_lists()
            p_u_41:reset_selected_item()
            p_u_41:transition_update_visual(0)
            p_u_41:layout()
        end;
        v_u_26.update_lists = function(_) --[[ Name: update_lists ]] --[[ Line: 128 ]]
            --[[ Upvalues: (copy 1): v_u_35, (copy 2): l__trade_local_protocol_0, (copy 3): p_u_23, (ref 4): v_u_14, (ref 5): v_u_16, (ref 6): v_u_22, (ref 7): v_u_20, (ref 8): v_u_33, (ref 9): v_u_15, (ref 10): v_u_30, (ref 11): v_u_31, (ref 12): v_u_34, (ref 13): v_u_17, (ref 14): v_u_37, (ref 15): v_u_32, (ref 16): v_u_39, (ref 17): v_u_38 ]]
            for _, v43 in v_u_35:key_itr() do
                for v44 = 1, v43:count() do
                    v43:get(v44):set_visible(false)
                end;
            end;
            local v45 = l__trade_local_protocol_0:get_active_trade_player_offer()
            local v46 = l__trade_local_protocol_0:get_active_trade_target_offer()
            local v47 = p_u_23._player_blob_manager:get_player_blob()
            local v48 = v_u_35:list_of(v_u_14.List.Inventory)
            local v49 = v_u_16:get_owned_crafting_materials(v47)
            v49:remove_if(function(_, p50) --[[ Line: 141 ]]
                --[[ Upvalues: (ref 1): v_u_22 ]]
                return v_u_22:singleton():is_material_tradeable(p50) ~= true;
            end)
            local v51 = v49:key_list()
            v51:sort(function(p52, p53) --[[ Line: 146 ]]
                --[[ Upvalues: (ref 1): v_u_20 ]]
                return v_u_20:materialid_get_type_sort_value(p53) > v_u_20:materialid_get_type_sort_value(p52) == false and -1 or 1;
            end)
            for v54 = 1, v48:count() do
                local v55 = v54 + v_u_33 * v48:count()
                if v55 <= v51:count() then
                    local v56 = v51:get(v55)
                    local v57 = v48:get(v54)
                    local v58 = v_u_15:get_material_id_playerblob_remaining_count(v45, v56, v47)
                    v57:set_material_id_and_count(v56, v58)
                    v57:set_visible(true)
                    if v58 <= 0 or v45:can_add_material(v56) ~= true then
                        v57:set_enabled(false)
                        v57:set_alpha(0.5)
                    end;
                end;
            end;
            v_u_30:set_visible(v_u_33 > 0)
            v_u_31:set_visible((v_u_33 + 1) * v_u_35:list_of(v_u_14.List.Inventory):count() < v51:count())
            v_u_34.Text = tostring(v_u_17:get_coin_currency(v47))
            local v59 = v45:get_materials_dict()
            local v60 = v59:key_list()
            local v61 = v_u_35:list_of(v_u_14.List.PlayerOffer)
            for v62 = 1, v61:count() do
                if v62 <= v60:count() then
                    local v63 = v61:get(v62)
                    local v64 = v60:get(v62)
                    v63:set_material_id_and_count(v64, v59:get(v64))
                    v63:set_visible(true)
                end;
            end;
            if v45:get_accepted() then
                v_u_37.Text = "Your Offer (Accepted)"
                v_u_32:set_visible(false)
            else
                v_u_37.Text = "Your Offer"
                v_u_32:set_visible(true)
            end;
            local v65 = v46:get_materials_dict()
            local v66 = v65:key_list()
            local v67 = v_u_35:list_of(v_u_14.List.TargetOffer)
            for v68 = 1, v67:count() do
                if v68 <= v66:count() then
                    local v69 = v67:get(v68)
                    local v70 = v66:get(v68)
                    v69:set_material_id_and_count(v70, v65:get(v70))
                    v69:set_visible(true)
                end;
            end;
            local _, v71 = l__trade_local_protocol_0:get_active_player_trade_target_info()
            v_u_39.Text = tostring(v46:get_coins())
            if v46:get_accepted() then
                v_u_38.Text = string.format("%s\'s Offer (Accepted)", v71)
            else
                v_u_38.Text = string.format("%s\'s Offer", v71)
            end;
        end;
        v_u_26.inventory_offset_page = function(p72, p73) --[[ Name: inventory_offset_page ]] --[[ Line: 221 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            v_u_33 = v_u_33 + p73
            p72:update_lists()
        end;
        v_u_26.list_element_pressed = function(p74, p75, p76) --[[ Name: list_element_pressed ]] --[[ Line: 226 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_23, (copy 3): l__trade_local_protocol_0, (ref 4): v_u_14, (ref 5): v_u_15, (ref 6): v_u_9 ]]
            if p76 <= 0 then
                v_u_8:warnf("list_element_pressed materialid(%d)", p76)
            else
                local v77 = p_u_23._player_blob_manager:get_player_blob()
                local v78 = l__trade_local_protocol_0:get_active_trade_player_offer()
                if p75 == v_u_14.List.Inventory then
                    if v_u_15:get_material_id_playerblob_remaining_count(v78, p76, v77) > 0 and v78:can_add_material(p76) then
                        p_u_23._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                        l__trade_local_protocol_0:player_offer_add_material(p76)
                        p74:update_lists()
                        return;
                    end;
                elseif p75 == v_u_14.List.PlayerOffer and v78:get_count_of_material_id(p76) > 0 then
                    p_u_23._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                    l__trade_local_protocol_0:player_offer_remove_material(p76)
                    p74:update_lists()
                end;
            end;
        end;
        v_u_26.accept_pressed = function(_) --[[ Name: accept_pressed ]] --[[ Line: 247 ]]
            --[[ Upvalues: (copy 1): v_u_40, (copy 2): l__trade_local_protocol_0, (ref 3): v_u_32 ]]
            if v_u_40:is_on_cooldown() ~= true then
                l__trade_local_protocol_0:player_accept()
                v_u_32:set_visible(false)
                v_u_40:add_cooldown(0.5)
            end;
        end;
        v_u_26.setup_list_elements = function(p_u_79) --[[ Name: setup_list_elements ]] --[[ Line: 255 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_4, (copy 3): p_u_23, (ref 4): v_u_14, (ref 5): v_u_6, (copy 6): p_u_24, (copy 7): v_u_35 ]]
            local l_InventoryItemProto_0 = v_u_27.InventoryItemProto
            l_InventoryItemProto_0.Parent = nil
            local function f_create_list_elements(p80, p81, p82) --[[ Name: create_list_elements ]] --[[ Line: 259 ]]
                --[[ Upvalues: (ref 1): v_u_4, (copy 2): l_InventoryItemProto_0, (ref 3): v_u_27, (copy 4): p_u_79, (ref 5): p_u_23, (ref 6): v_u_14, (ref 7): v_u_6, (ref 8): p_u_24, (ref 9): v_u_35 ]]
                local v83 = v_u_4:new()
                for v84 = 1, p81 do
                    v83:push_back(p80:FindFirstChild(string.format("Anchor%d", v84)))
                end;
                for v85 = 1, v83:count() do
                    local v86 = v83:get(v85)
                    local v87 = l_InventoryItemProto_0:Clone()
                    v87.Name = string.format("InventoryItemProto_List(%d)_i(%d)", p82, v85)
                    v87.Parent = v_u_27
                    v87.Position = v86.Position
                    local v88 = p_u_79:add_cycle_element(p_u_23, 1, v_u_14:new(v_u_6:new(p_u_79, v_u_27.PrimaryPart, v87), p_u_24, p82, v85, p_u_79))
                    v_u_35:push_back_to(p82, v88)
                    v88:set_visible(false)
                end;
            end;
            f_create_list_elements(v_u_27.InventorySectionAnchors, 9, v_u_14.List.Inventory)
            f_create_list_elements(v_u_27.PlayerOfferAnchors, 6, v_u_14.List.PlayerOffer)
            f_create_list_elements(v_u_27.TargetOfferAnchors, 6, v_u_14.List.TargetOffer)
        end;
        local v_u_89 = false
        local function f_handle_trade_local_protocol_processing() --[[ Name: handle_trade_local_protocol_processing ]] --[[ Line: 289 ]]
            --[[ Upvalues: (ref 1): v_u_89, (copy 2): p_u_25, (copy 3): v_u_26, (copy 4): p_u_23, (copy 5): l__trade_local_protocol_0, (ref 6): v_u_2, (ref 7): v_u_13, (copy 8): p_u_24, (ref 9): v_u_12, (ref 10): v_u_9 ]]
            if v_u_89 == false then
                v_u_89 = true
                p_u_25:remove_menu(v_u_26)
                local v_u_90 = nil
                local v_u_91 = false
                local function _(p_u_92) --[[ Name: sync_playerblob_and_close_loading_menu ]] --[[ Line: 298 ]]
                    --[[ Upvalues: (ref 1): v_u_91, (ref 2): p_u_23, (ref 3): p_u_25, (ref 4): v_u_90, (ref 5): l__trade_local_protocol_0 ]]
                    if v_u_91 == false then
                        v_u_91 = true
                        p_u_23._player_blob_manager:do_sync(function() --[[ Line: 301 ]]
                            --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_90, (copy 3): p_u_92, (ref 4): l__trade_local_protocol_0 ]]
                            p_u_25:remove_menu(v_u_90)
                            p_u_92()
                            l__trade_local_protocol_0:stop()
                        end)
                    end;
                end;
                local v_u_93 = v_u_2:new()
                v_u_90 = p_u_25:push_menu(v_u_13:new(p_u_23, p_u_24, p_u_25):set_text("Processing...", ""):set_close_button_visible(false):set_update_fn(function() --[[ Line: 313 ]]
                    --[[ Upvalues: (ref 1): v_u_91, (copy 2): v_u_93, (ref 3): l__trade_local_protocol_0, (ref 4): v_u_12, (ref 5): v_u_13, (ref 6): p_u_23, (ref 7): p_u_24, (ref 8): p_u_25, (ref 9): v_u_90, (ref 10): v_u_9 ]]
                    if v_u_91 then
                        return;
                    elseif v_u_93:contains(l__trade_local_protocol_0:get_current_mode()) then
                        return;
                    elseif l__trade_local_protocol_0:get_current_mode() == v_u_12.Mode.ActivePlayerTradeConfirmRequired then
                        v_u_93:add_set(l__trade_local_protocol_0:get_current_mode())
                        local v_u_94 = nil
                        v_u_94 = v_u_13:new(p_u_23, p_u_24, p_u_25):set_text("Confirm trade?", string.format("Confirm trade (%s) for (%s)?", l__trade_local_protocol_0:get_active_trade_player_offer():to_string(), l__trade_local_protocol_0:get_active_trade_target_offer():to_string())):set_okay_button_fn(function() --[[ Line: 329 ]]
                            --[[ Upvalues: (ref 1): l__trade_local_protocol_0, (ref 2): p_u_25, (ref 3): v_u_94 ]]
                            l__trade_local_protocol_0:trade_confirm(true)
                            p_u_25:remove_menu(v_u_94)
                        end):set_cancel_button_fn(function() --[[ Line: 333 ]]
                            --[[ Upvalues: (ref 1): l__trade_local_protocol_0, (ref 2): p_u_25, (ref 3): v_u_94 ]]
                            l__trade_local_protocol_0:trade_confirm(false)
                            p_u_25:remove_menu(v_u_94)
                        end):set_update_fn(function() --[[ Line: 337 ]]
                            --[[ Upvalues: (ref 1): l__trade_local_protocol_0, (ref 2): v_u_12, (ref 3): p_u_25, (ref 4): v_u_94 ]]
                            if l__trade_local_protocol_0:get_current_mode() ~= v_u_12.Mode.ActivePlayerTradeConfirmRequired then
                                p_u_25:remove_menu(v_u_94)
                            end;
                        end)
                        p_u_25:push_menu(v_u_94)
                        return;
                    elseif l__trade_local_protocol_0:get_current_mode() == v_u_12.Mode.ActivePlayerTradeConfirmSent then
                        v_u_93:add_set(l__trade_local_protocol_0:get_current_mode())
                        local v_u_95 = nil
                        local v96 = v_u_13:new(p_u_23, p_u_24, p_u_25):set_text("Waiting...", "Waiting on the other player to confirm..."):set_cancel_button_fn(function() --[[ Line: 353 ]]
                            --[[ Upvalues: (ref 1): l__trade_local_protocol_0, (ref 2): p_u_25, (ref 3): v_u_95 ]]
                            l__trade_local_protocol_0:trade_confirm(false)
                            p_u_25:remove_menu(v_u_95)
                        end):set_update_fn(function() --[[ Line: 357 ]]
                            --[[ Upvalues: (ref 1): l__trade_local_protocol_0, (ref 2): v_u_12, (ref 3): p_u_25, (ref 4): v_u_95 ]]
                            if l__trade_local_protocol_0:get_current_mode() ~= v_u_12.Mode.ActivePlayerTradeConfirmSent then
                                p_u_25:remove_menu(v_u_95)
                            end;
                        end)
                        p_u_25:push_menu(v96)
                    elseif l__trade_local_protocol_0:get_current_mode() == v_u_12.Mode.Error then
                        local function v_u_97() --[[ Line: 365 ]]
                            --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_13, (ref 3): p_u_23, (ref 4): p_u_24, (ref 5): l__trade_local_protocol_0 ]]
                            p_u_25:push_menu(v_u_13:new(p_u_23, p_u_24, p_u_25):set_text("Trade Failed", l__trade_local_protocol_0:get_errmsg()))
                        end;
                        if v_u_91 == false then
                            v_u_91 = true
                            p_u_23._player_blob_manager:do_sync(function() --[[ Line: 301 ]]
                                --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_90, (copy 3): v_u_97, (ref 4): l__trade_local_protocol_0 ]]
                                p_u_25:remove_menu(v_u_90)
                                v_u_97()
                                l__trade_local_protocol_0:stop()
                            end)
                            return;
                        end;
                    elseif l__trade_local_protocol_0:get_current_mode() == v_u_12.Mode.ActivePlayerTradeComplete then
                        local function v_u_98() --[[ Line: 370 ]]
                            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_9, (ref 3): p_u_25, (ref 4): v_u_13, (ref 5): p_u_24, (ref 6): l__trade_local_protocol_0 ]]
                            p_u_23._sfx_manager:play_sfx(v_u_9.SFX_ACQUIRE)
                            p_u_25:push_menu(v_u_13:new(p_u_23, p_u_24, p_u_25):set_text("Trade Complete", string.format("Traded (%s) for (%s)!", l__trade_local_protocol_0:get_active_trade_player_offer():to_string(), l__trade_local_protocol_0:get_active_trade_target_offer():to_string())))
                        end;
                        if v_u_91 == false then
                            v_u_91 = true
                            p_u_23._player_blob_manager:do_sync(function() --[[ Line: 301 ]]
                                --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_90, (copy 3): v_u_98, (ref 4): l__trade_local_protocol_0 ]]
                                p_u_25:remove_menu(v_u_90)
                                v_u_98()
                                l__trade_local_protocol_0:stop()
                            end)
                        end;
                    end;
                end))
            end;
        end;
        local v_u_99 = 0
        local v_u_100 = 0
        local l_NO_UPDATE_TIME_0 = v_u_12.NO_UPDATE_TIME
        v_u_26.behaviour_update = function(p101, p102, _) --[[ Name: behaviour_update ]] --[[ Line: 390 ]]
            --[[ Upvalues: (copy 1): p_u_23, (copy 2): l__trade_local_protocol_0, (ref 3): v_u_12, (copy 4): f_handle_trade_local_protocol_processing, (copy 5): v_u_40, (ref 6): v_u_36, (ref 7): v_u_17, (ref 8): v_u_99, (ref 9): v_u_100, (ref 10): v_u_19, (ref 11): v_u_11, (ref 12): l_NO_UPDATE_TIME_0 ]]
            p101:behaviour_update_base(p102, p_u_23)
            if l__trade_local_protocol_0:get_current_mode() == v_u_12.Mode.ActivePlayerTradeProcessing or (l__trade_local_protocol_0:get_current_mode() == v_u_12.Mode.ActivePlayerTradeComplete or (l__trade_local_protocol_0:get_current_mode() == v_u_12.Mode.ActivePlayerTradeConfirmRequired or (l__trade_local_protocol_0:get_current_mode() == v_u_12.Mode.ActivePlayerTradeConfirmSent or l__trade_local_protocol_0:get_current_mode() == v_u_12.Mode.Error))) then
                f_handle_trade_local_protocol_processing()
            else
                v_u_40:update(p102)
                v_u_36:update(p102)
                if v_u_36:raise_changed() == true then
                    local v103 = p_u_23._player_blob_manager:get_player_blob()
                    local v104 = tonumber(v_u_36:get_current_text())
                    local v105 = v104 == nil and 0 or v104
                    local v106 = v_u_17:get_coin_currency(v103)
                    if v106 < v105 then
                        v_u_36:do_unfocus()
                        v_u_36:set_text((tostring(v106)))
                    else
                        v106 = v105
                    end;
                    v_u_99 = v106
                    v_u_100 = v_u_19.TRADE_UPDATE_COOLDOWN_TIME_SEC
                end;
                if v_u_100 > 0 then
                    v_u_100 = v_u_100 - v_u_11:TimescaleToDeltaTime(p102)
                    if v_u_100 <= 0 then
                        l__trade_local_protocol_0:player_offer_set_coins(v_u_99)
                    end;
                end;
                if l__trade_local_protocol_0:get_last_updated_time() ~= l_NO_UPDATE_TIME_0 then
                    l_NO_UPDATE_TIME_0 = l__trade_local_protocol_0:get_last_updated_time()
                    p101:update_lists()
                end;
            end;
        end;
        v_u_26.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 435 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_27 ]]
            v_u_36:cleanup()
            v_u_27:Destroy()
        end;
        v_u_26.layout = function(p107) --[[ Name: layout ]] --[[ Line: 440 ]]
            --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_29, (ref 3): v_u_27, (copy 4): v_u_35 ]]
            p107:opt_rescale_to_max_nxy(p_u_24, 0.825, 0.825, v_u_29)
            local v108, v109 = p107:opt_update_cframe_params(p_u_24, {
                ["PositionNXY"] = Vector2.new(0.475, 0.5),
                ["OffsetXYZ"] = p107:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v108 == true then
                v_u_27:SetPrimaryPartCFrame(v109)
            end;
            for _, v110 in v_u_35:key_itr() do
                for v111 = 1, v110:count() do
                    v110:get(v111):layout()
                end;
            end;
        end;
        v_u_26.set_alpha = function(_, p112) --[[ Name: set_alpha ]] --[[ Line: 458 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_1, (ref 3): v_u_27 ]]
            if v_u_28 ~= p112 then
                v_u_28 = p112
                v_u_1:r_set_alpha(v_u_27, v_u_28)
            end;
        end;
        v_u_26.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 464 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28;
        end;
        v_u_26.set_scale = function(_, p113) --[[ Name: set_scale ]] --[[ Line: 465 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            v_u_29 = p113
        end;
        v_u_26.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 466 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            return v_u_29;
        end;
        v_u_26.get_native_size = function(p114) --[[ Name: get_native_size ]] --[[ Line: 468 ]]
            return p114._native_size;
        end;
        v_u_26.get_size = function(p115) --[[ Name: get_size ]] --[[ Line: 471 ]]
            return p115._size;
        end;
        v_u_26.set_size = function(p116, p117) --[[ Name: set_size ]] --[[ Line: 474 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            p116._size = p117
            v_u_27.PrimaryPart.Size = Vector3.new(p117.X, p117.Y, 0)
        end;
        v_u_26.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 478 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27.PrimaryPart.Position;
        end;
        v_u_26.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 481 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27.PrimaryPart.SurfaceGui;
        end;
        v_u_26:cons()
        return v_u_26;
    end
};
