-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:41 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIButton)
local v_u_4 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
local v_u_10 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_12 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.CraftingUISearchSection)
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
local v_u_16 = nil
v14:require_client(function() --[[ Line: 28 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16 ]]
    v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
end)
local v_u_17 = {
    ["Mode"] = {
        ["Closed"] = 1,
        ["InfoRequest"] = 2,
        ["Ready"] = 3
    }
}
local v_u_18 = 1
v_u_17.new = function(_, p_u_19, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 43 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_17, (copy 3): v_u_1, (copy 4): v_u_7, (copy 5): v_u_3, (copy 6): v_u_8, (copy 7): v_u_10, (ref 8): v_u_18, (copy 9): v_u_6, (copy 10): v_u_5, (copy 11): v_u_4, (copy 12): v_u_12, (copy 13): v_u_13, (copy 14): v_u_11, (ref 15): v_u_15, (ref 16): v_u_16, (copy 17): v_u_9 ]]
    local v_u_22 = v_u_2:new(p_u_20, p_u_21)
    local v_u_23 = nil
    local l__shop_local_protocol_0 = p_u_19._shop_local_protocol
    local l_InfoRequest_0 = v_u_17.Mode.InfoRequest
    local function _() --[[ Name: request_response_kill ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_17 ]]
        return l_InfoRequest_0 == v_u_17.Mode.Closed;
    end;
    local v_u_24 = 1
    local v_u_25 = 1
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = {}
    local function f_cons() --[[ Name: cons ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_1, (ref 3): v_u_7, (copy 4): v_u_22, (ref 5): v_u_26, (ref 6): v_u_3, (copy 7): p_u_20, (copy 8): p_u_19, (ref 9): v_u_8, (ref 10): v_u_34, (ref 11): v_u_35, (ref 12): l_InfoRequest_0, (ref 13): v_u_17, (copy 14): p_u_21, (ref 15): v_u_10, (ref 16): v_u_28, (ref 17): v_u_27, (ref 18): v_u_32, (ref 19): v_u_33, (ref 20): v_u_29, (ref 21): v_u_30, (ref 22): v_u_31, (copy 23): l__shop_local_protocol_0, (ref 24): v_u_36, (ref 25): v_u_18 ]]
        v_u_23 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.CraftingGatchaUI:Clone()
        v_u_23.Name = v_u_1:gen_name(v_u_23.Name)
        v_u_23.Parent = v_u_7:get_world_ui_folder()
        v_u_22._native_size = v_u_23.PrimaryPart.Size
        v_u_22._size = v_u_22._native_size
        v_u_26 = v_u_3:new(v_u_23.RollButtonSurface, p_u_20, function() --[[ Line: 78 ]]
            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_8, (ref 3): v_u_22 ]]
            p_u_19._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
            v_u_22:do_gatcha_roll()
        end)
        v_u_26:set_position_nxy(0.5, 0.5)
        v_u_26:set_anchor_rnxy(0.5, 0.5)
        v_u_26:set_passive_anim()
        v_u_22:add_cycle_element(p_u_19, 1, v_u_26)
        v_u_34 = v_u_22:add_cycle_element(p_u_19, 1, v_u_3:new(v_u_23.LeftArrowSurface, p_u_20, function() --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_8, (ref 3): v_u_22 ]]
            p_u_19._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_22:increment_selected_gatcha(-1)
        end):set_position_nxy(0.5, 0.5):set_anchor_rnxy(0.5, 0.5):set_position_offset_xy(-1.95, 0))
        v_u_35 = v_u_22:add_cycle_element(p_u_19, 1, v_u_3:new(v_u_23.RightArrowSurface, p_u_20, function() --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_8, (ref 3): v_u_22 ]]
            p_u_19._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_22:increment_selected_gatcha(1)
        end):set_position_nxy(0.5, 0.5):set_anchor_rnxy(0.5, 0.5):set_position_offset_xy(1.95, 0))
        local v_u_37 = v_u_3:new(v_u_23.BackButtonSurface, p_u_20, function() --[[ Line: 120 ]]
            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_8, (ref 3): l_InfoRequest_0, (ref 4): v_u_17, (ref 5): v_u_22, (ref 6): p_u_21 ]]
            p_u_19._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
            l_InfoRequest_0 = v_u_17.Mode.Closed
            v_u_22:reset_starmachine_npc()
            p_u_21:remove_menu(v_u_22)
        end)
        v_u_37:set_position_nxy(0.95, 0.05)
        v_u_37:set_anchor_rnxy(0.5, 0.5)
        v_u_37:set_pre_layout_fn(function() --[[ Line: 129 ]]
            --[[ Upvalues: (copy 1): v_u_37 ]]
            local v38 = v_u_37:get_native_size()
            v_u_37:set_position_offset_xy(-v38.X * 0.5, -v38.Y * 0.5)
        end)
        v_u_22:add_cycle_element(p_u_19, 1, v_u_37)
        v_u_22:set_alpha(0)
        p_u_19._npcs:try_get_npc(v_u_10.NPC.NPC_NoteMachine, function(p39) --[[ Line: 139 ]]
            p39:stop_anim()
        end)
        p_u_19:set_character_random_position_around_anchors_fn(function() --[[ Line: 144 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7:get_lobby_anchors().GearShop.Gatcha.StandAnchor, v_u_7:get_lobby_anchors().GearShop.Gatcha.LookAnchor;
        end)
        p_u_19:transition_local_camera_to_anchors_fn(function() --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7:get_lobby_anchors().GearShop.Gatcha.CameraAnchor, v_u_7:get_lobby_anchors().GearShop.Gatcha.LookAnchor;
        end)
        v_u_28 = v_u_23.MainSurface.SurfaceGui.Frame.CoinSection.Display
        v_u_27 = v_u_23.MainSurface.SurfaceGui.Frame.StarSection.Display
        v_u_32 = v_u_23.RollButtonSurface.Part.SurfaceGui.Frame.Icon
        v_u_33 = v_u_23.MainSurface.SurfaceGui.Frame.ProbDesc
        v_u_33.Text = ""
        v_u_29 = v_u_23.RollButtonSurface.Part.SurfaceGui.Frame.PriceDisplay
        v_u_30 = v_u_23.RollButtonSurface.Part.SurfaceGui.Frame.CountDisplay
        v_u_31 = v_u_23.RollButtonSurface.Part.SurfaceGui.Frame.BonusDisplay
        v_u_22:update_blob_sync()
        l_InfoRequest_0 = v_u_17.Mode.InfoRequest
        v_u_22:update_ui_mode()
        l__shop_local_protocol_0:request_crafting_gatcha_info(function(p40) --[[ Line: 166 ]]
            --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_17, (ref 3): v_u_36, (ref 4): v_u_18, (ref 5): v_u_1, (ref 6): v_u_22 ]]
            if l_InfoRequest_0 ~= v_u_17.Mode.Closed then
                l_InfoRequest_0 = v_u_17.Mode.Ready
                v_u_36 = p40
                v_u_18 = v_u_1:clamp(v_u_18, 1, #v_u_36)
                v_u_22:update_ui_mode()
            end;
        end)
    end;
    v_u_22.update_ui_mode = function(_) --[[ Name: update_ui_mode ]] --[[ Line: 175 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_17, (ref 3): v_u_26, (ref 4): v_u_34, (ref 5): v_u_35, (ref 6): v_u_36, (ref 7): v_u_18, (ref 8): v_u_29, (ref 9): v_u_1, (ref 10): v_u_6, (ref 11): v_u_32, (ref 12): v_u_33, (ref 13): v_u_30, (ref 14): v_u_31 ]]
        if l_InfoRequest_0 == v_u_17.Mode.InfoRequest then
            v_u_26:get_sgui().Enabled = false
            v_u_26:set_selectable(false)
            v_u_34:set_visible(false)
            v_u_35:set_visible(false)
        else
            v_u_26:get_sgui().Enabled = true
            v_u_26:set_selectable(true)
            local v41 = v_u_36[v_u_18]
            v_u_29.Text = v_u_1:comma_value(v41.PriceValue)
            v_u_6:currency_type_render_icon(v41.PriceType, v_u_32)
            if v41.PriceType == v_u_6.CurrencyType.Coins then
                v_u_33.Text = "(45% Small Note, 30% Medium Note, 14% Large Note, 7% Gem, 2% Protect, 2% Boost)"
            else
                v_u_33.Text = "(60% Medium Note, 20% Large Note, 10% Gem, 5% Protect, 5% Boost)"
            end;
            v_u_30.Text = string.format("x%d", v41.SpinCount)
            if v41.ExtraDisplay == nil then
                v_u_31.Text = ""
            else
                v_u_31.Text = string.format("+%d Bonus", v41.ExtraDisplay)
            end;
            v_u_34:set_visible(true)
            v_u_35:set_visible(true)
        end;
    end;
    v_u_22.increment_selected_gatcha = function(p42, p43) --[[ Name: increment_selected_gatcha ]] --[[ Line: 204 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_5, (ref 3): v_u_36, (ref 4): v_u_26 ]]
        v_u_18 = v_u_5:wrap_val(v_u_18 + p43, 1, #v_u_36 + 1)
        v_u_26:set_scale(1.15)
        p42:update_ui_mode()
    end;
    v_u_22.do_gatcha_roll = function(_) --[[ Name: do_gatcha_roll ]] --[[ Line: 210 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_4, (copy 3): p_u_19, (copy 4): p_u_20, (copy 5): l__shop_local_protocol_0, (ref 6): v_u_18, (ref 7): v_u_12, (ref 8): v_u_13, (ref 9): v_u_11, (ref 10): v_u_15, (ref 11): v_u_16, (ref 12): v_u_36, (ref 13): v_u_9 ]]
        local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_4, (ref 3): p_u_19, (ref 4): p_u_20, (ref 5): l__shop_local_protocol_0, (ref 6): v_u_18, (ref 7): v_u_12, (ref 8): v_u_13, (ref 9): v_u_11, (ref 10): v_u_15, (ref 11): v_u_16 ]]
            local v_u_44 = p_u_21:push_menu(v_u_4:new(p_u_19, p_u_20, p_u_21):set_text("Rolling...", ""):set_close_button_visible(false))
            l__shop_local_protocol_0:try_purchase_crafting_gatcha(v_u_18, function(p45, p46, p_u_47) --[[ Line: 214 ]]
                --[[ Upvalues: (ref 1): p_u_21, (copy 2): v_u_44, (ref 3): v_u_4, (ref 4): p_u_19, (ref 5): p_u_20, (ref 6): v_u_12, (ref 7): v_u_13, (ref 8): v_u_11, (ref 9): v_u_15, (ref 10): v_u_16 ]]
                if p45 == true then
                    p_u_19._player_blob_manager:do_sync(function() --[[ Line: 221 ]]
                        --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_44, (ref 3): v_u_12, (copy 4): p_u_47, (ref 5): v_u_13, (ref 6): v_u_11, (ref 7): v_u_15, (ref 8): p_u_19, (ref 9): p_u_20, (ref 10): v_u_16 ]]
                        p_u_21:remove_menu(v_u_44)
                        local v48 = v_u_12.RewardInfo:table_to_list(p_u_47)
                        v48:sort(function(p49, p50) --[[ Line: 224 ]]
                            --[[ Upvalues: (ref 1): v_u_13 ]]
                            return v_u_13:materialid_get_type_sort_value(p50:get_id()) > v_u_13:materialid_get_type_sort_value(p49:get_id()) == false and -1 or 1;
                        end)
                        if v_u_11.UseRewardDescriptionInfoAcquiredUI == true then
                            p_u_21:push_menu(v_u_15:new(p_u_19, p_u_20, p_u_21, v48):set_header_text("Materials Acquired!"):set_sub_text("Acquired the following materials from the Note Machine..."))
                        else
                            p_u_21:push_menu(v_u_16:new(p_u_19, p_u_20, p_u_21, v48))
                        end;
                    end)
                else
                    p_u_21:remove_menu(v_u_44)
                    p_u_21:push_menu(v_u_4:new(p_u_19, p_u_20, p_u_21):set_text("Purchase Failed", p46))
                end;
            end)
        end;
        local v51 = v_u_36[v_u_18]
        local v52 = v_u_9:playerblob_purchase_needs_redirect(p_u_19._player_blob_manager:get_player_blob(), v51.PriceType, v51.PriceValue)
        if v52:is_valid() then
            v_u_9:show_purchase_redirect(p_u_19, v52, function(p53) --[[ Line: 248 ]]
                --[[ Upvalues: (copy 1): f_do_purchase ]]
                if p53 then
                    f_do_purchase()
                end;
            end)
        else
            f_do_purchase()
        end;
    end;
    local v_u_54 = -1
    v_u_22.update_blob_sync = function(_) --[[ Name: update_blob_sync ]] --[[ Line: 259 ]]
        --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_54, (ref 3): v_u_28, (ref 4): v_u_1, (ref 5): v_u_27 ]]
        if p_u_19._player_blob_manager:is_synced() and p_u_19._player_blob_manager:get_synced_time() ~= v_u_54 then
            v_u_54 = p_u_19._player_blob_manager:get_synced_time()
            local v55 = p_u_19._player_blob_manager:get_player_blob()
            v_u_28.Text = v_u_1:comma_value(v55.CoinCurrency)
            v_u_27.Text = v_u_1:comma_value(v55.StarCurrency)
        end;
    end;
    local v_u_56 = false
    v_u_22.visual_update = function(p57, p58, p59) --[[ Name: visual_update ]] --[[ Line: 270 ]]
        --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_56, (ref 3): v_u_10 ]]
        if p_u_19:transition_local_camera_cframe_finished() ~= false then
            if v_u_56 == false then
                v_u_56 = true
                p_u_19._npcs:try_get_npc(v_u_10.NPC.NPC_NoteMachine, function(p60) --[[ Line: 277 ]]
                    p60:show_fade_back(true)
                    p60:show_face_machine_selected()
                end)
            end;
            p57:visual_update_base(p58, p59)
        end;
    end;
    v_u_22.behaviour_update = function(p61, p62, p63) --[[ Name: behaviour_update ]] --[[ Line: 286 ]]
        p61:behaviour_update_base(p62, p63)
        p61:update_blob_sync()
    end;
    v_u_22.layout = function(p64) --[[ Name: layout ]] --[[ Line: 292 ]]
        --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_25, (ref 3): v_u_23 ]]
        p_u_20:uiobj_rescale_to_max_nxy(p64, 0.5, 0.3, v_u_25)
        v_u_23:SetPrimaryPartCFrame(p_u_20:get_cframe({
            ["PositionNXY"] = Vector2.new(0.025, 0.95),
            ["OffsetXYZ"] = p64:anchored_offset(0, 1),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
    end;
    v_u_22.reset_starmachine_npc = function(_) --[[ Name: reset_starmachine_npc ]] --[[ Line: 301 ]]
        --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_10 ]]
        p_u_19._npcs:try_get_npc(v_u_10.NPC.NPC_NoteMachine, function(p65) --[[ Line: 302 ]]
            p65:show_fade_back(false)
            p65:play_idle_anim()
            p65:show_face_neutral()
        end)
    end;
    v_u_22.do_remove = function(p66, _) --[[ Name: do_remove ]] --[[ Line: 309 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        p66:reset_starmachine_npc()
        v_u_23:Destroy()
    end;
    v_u_22.set_alpha = function(_, p67) --[[ Name: set_alpha ]] --[[ Line: 314 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_1, (ref 3): v_u_23 ]]
        if v_u_24 ~= p67 then
            v_u_24 = p67
            v_u_1:r_set_alpha(v_u_23, v_u_24)
        end;
    end;
    v_u_22.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 320 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24;
    end;
    v_u_22.set_scale = function(_, p68) --[[ Name: set_scale ]] --[[ Line: 321 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        v_u_25 = p68
    end;
    v_u_22.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 322 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25;
    end;
    v_u_22.get_native_size = function(p69) --[[ Name: get_native_size ]] --[[ Line: 324 ]]
        return p69._native_size;
    end;
    v_u_22.get_size = function(p70) --[[ Name: get_size ]] --[[ Line: 327 ]]
        return p70._size;
    end;
    v_u_22.set_size = function(p71, p72) --[[ Name: set_size ]] --[[ Line: 330 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        p71._size = p72
        v_u_23.PrimaryPart.Size = Vector3.new(p72.X, p72.Y, 0)
    end;
    v_u_22.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 334 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        return v_u_23.PrimaryPart.Position;
    end;
    v_u_22.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 337 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        return v_u_23.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_22;
end;
return v_u_17;
