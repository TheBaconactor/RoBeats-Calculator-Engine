-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:43 PM
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
require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_9 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.PurchaseUtils)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v_u_15 = {
    ["Mode"] = {
        ["Loading"] = 1,
        ["Loaded"] = 2
    }
}
v_u_15.new = function(_, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 28 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_15, (copy 3): v_u_3, (copy 4): v_u_1, (copy 5): v_u_8, (copy 6): v_u_6, (copy 7): v_u_5, (copy 8): v_u_7, (copy 9): v_u_9, (copy 10): v_u_2, (copy 11): v_u_14, (copy 12): v_u_10, (copy 13): v_u_12, (copy 14): v_u_11, (copy 15): v_u_13 ]]
    local v19 = v_u_4:new(p_u_17, p_u_18)
    local v_u_20 = nil
    local v_u_21 = 1
    local v_u_22 = 1
    local l_Loading_0 = v_u_15.Mode.Loading
    local v_u_23 = nil
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = v_u_3:new()
    v19.cons = function(p_u_27) --[[ Name: cons ]] --[[ Line: 43 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_1, (ref 3): v_u_8, (ref 4): v_u_24, (ref 5): v_u_23, (ref 6): v_u_25, (copy 7): p_u_16, (ref 8): v_u_6, (ref 9): v_u_5, (copy 10): p_u_17, (ref 11): v_u_7, (copy 12): p_u_18, (ref 13): v_u_9, (ref 14): v_u_2, (ref 15): v_u_14, (ref 16): v_u_10, (copy 17): v_u_26, (ref 18): l_Loading_0, (ref 19): v_u_15 ]]
        v_u_20 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.VIPPurchaseUI:Clone()
        v_u_20.Name = v_u_1:gen_name(v_u_20.Name)
        v_u_20.Parent = v_u_8:get_world_ui_folder()
        p_u_27._native_size = v_u_20.PrimaryPart.Size
        p_u_27._size = p_u_27._native_size
        v_u_24 = v_u_20.PrimaryPart.SurfaceGui.Frame.LoadingFrame
        v_u_23 = v_u_20.PrimaryPart.SurfaceGui.Frame.LoadedFrame
        v_u_25 = v_u_23.SubscriptionStatusDisplay
        p_u_27:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(p_u_27, v_u_20.PrimaryPart, v_u_20.BackButtonSurface), p_u_17, function() --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_7, (ref 3): p_u_18, (copy 4): p_u_27 ]]
            p_u_16._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            p_u_18:remove_menu(p_u_27)
        end))
        p_u_27:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(p_u_27, v_u_20.PrimaryPart, v_u_20.BonusSectionSongButton), p_u_17, function() --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_7, (ref 3): p_u_18, (ref 4): v_u_9, (ref 5): p_u_17 ]]
            p_u_16._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            p_u_18:push_menu(v_u_9:new(p_u_16, p_u_17, p_u_18):set_text("Play Any Song...", "While your VIP is active, you\'ll be able to play EVERY song in the RoBeats catalog! These will be accessible from the Play menu."))
        end))
        p_u_27:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(p_u_27, v_u_20.PrimaryPart, v_u_20.BonusSectionMoneyButton), p_u_17, function() --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_7, (ref 3): p_u_18, (ref 4): v_u_9, (ref 5): p_u_17 ]]
            p_u_16._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            p_u_18:push_menu(v_u_9:new(p_u_16, p_u_17, p_u_18):set_text("More for your Money...", "While your VIP is active, you\'ll get the following bonuses...\n* x2 Coins per match\n* 10% More event points per match\n* 10% More Mini EXP per match\n* 10% More Mini EXP when training\n* Reduced price on Marketplace sales"))
        end))
        p_u_27:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(p_u_27, v_u_20.PrimaryPart, v_u_20.BonusSectionExclusiveButton), p_u_17, function() --[[ Line: 97 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_7, (ref 3): p_u_18, (ref 4): v_u_9, (ref 5): p_u_17 ]]
            p_u_16._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            p_u_18:push_menu(v_u_9:new(p_u_16, p_u_17, p_u_18):set_text("VIP Exclusives...", "While your VIP is active, you\'ll have access to...\n* VIP-exclusive tiers in the monthly Challenge Pass\n* VIP-exclusive title and icon"))
        end))
        local v28 = v_u_2:new()
        local v29 = p_u_16._player_blob_manager:get_day_event_list():is_event_type_active(v_u_14.EventType.VIPSale)
        if v29 then
            v28:add_table({
                [v_u_10.ProductID_VIP_1Month_Sale50] = v_u_20.Tier1Button,
                [v_u_10.ProductID_VIP_3Month_Sale50] = v_u_20.Tier2Button,
                [v_u_10.ProductID_VIP_6Month_Sale50] = v_u_20.Tier3Button
            })
            v_u_23.SaleOverlay.Visible = true
        else
            v28:add_table({
                [v_u_10.ProductID_VIP_1Month] = v_u_20.Tier1Button,
                [v_u_10.ProductID_VIP_3Month] = v_u_20.Tier2Button,
                [v_u_10.ProductID_VIP_6Month] = v_u_20.Tier3Button
            })
            v_u_23.SaleOverlay.Visible = false
        end;
        for v_u_30, v31 in v28:key_itr() do
            v31.SurfaceGui.Frame.RobuxDisplay.TextLabel.Text = tostring(v_u_10:get_info_data_for_productid(v_u_30):get_robux_cost())
            v31.SurfaceGui.Frame.SaleOverlay.Visible = v29
            v_u_26:push_back(p_u_27:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(p_u_27, v_u_20.PrimaryPart, v31), p_u_17, function() --[[ Line: 132 ]]
                --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_7, (copy 3): p_u_27, (copy 4): v_u_30 ]]
                p_u_16._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                p_u_27:purchase_button_pressed(v_u_30)
            end)):set_auto_zoffset_behaviour(true))
        end;
        l_Loading_0 = v_u_15.Mode.Loaded
        p_u_27:update_visual()
        p_u_27:transition_update_visual(0)
        p_u_27:layout()
    end;
    v19.update_visual = function(_) --[[ Name: update_visual ]] --[[ Line: 147 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_15, (ref 3): v_u_23, (ref 4): v_u_24, (copy 5): v_u_26, (copy 6): p_u_16, (ref 7): v_u_12, (ref 8): v_u_25 ]]
        if l_Loading_0 == v_u_15.Mode.Loading then
            v_u_23.Visible = false
            v_u_24.Visible = true
            for v32 = 1, v_u_26:count() do
                v_u_26:get(v32):set_visible(false)
            end;
        else
            v_u_23.Visible = true
            v_u_24.Visible = false
            for v33 = 1, v_u_26:count() do
                v_u_26:get(v33):set_visible(true)
            end;
        end;
        local v34 = p_u_16._player_blob_manager:get_player_blob()
        if v34 == nil or not v_u_12:playerblob_has_vip_for_current_day(v34, p_u_16:get_current_dayid()) then
            v_u_25.Text = ""
        else
            v_u_25.Text = string.format("Thank you for subscribing to Robeats VIP! You have %d day(s) remaining in your subscription.", v_u_12:playerblob_get_remaining_vip_days_for_current_day(v34, p_u_16:get_current_dayid()))
        end;
    end;
    v19.purchase_button_pressed = function(p_u_35, p36) --[[ Name: purchase_button_pressed ]] --[[ Line: 173 ]]
        --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_10, (ref 3): v_u_13, (copy 4): p_u_16, (copy 5): p_u_17, (copy 6): p_u_18, (ref 7): l_Loading_0, (ref 8): v_u_15, (ref 9): v_u_7 ]]
        v_u_11:is_enum_member(p36, v_u_10)
        v_u_13:purchase_prompt(p_u_16, p_u_17, p_u_18, p36, function() --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_15, (copy 3): p_u_35, (ref 4): p_u_16, (ref 5): v_u_7 ]]
            l_Loading_0 = v_u_15.Mode.Loaded
            p_u_35:update_visual()
            p_u_16._sfx_manager:play_sfx(v_u_7.SFX_FANFARE)
        end)
    end;
    v19.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 183 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        v_u_20:Destroy()
    end;
    v19.behaviour_update = function(p37, p38, p39) --[[ Name: behaviour_update ]] --[[ Line: 187 ]]
        p37:behaviour_update_base(p38, p39)
    end;
    v19.layout = function(p40) --[[ Name: layout ]] --[[ Line: 191 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_22, (ref 3): v_u_20 ]]
        p40:opt_rescale_to_max_nxy(p_u_17, 0.85, 0.85, v_u_22)
        local v41, v42 = p40:opt_update_cframe_params(p_u_17, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p40:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v41 == true then
            v_u_20:SetPrimaryPartCFrame(v42)
        end;
    end;
    v19.set_alpha = function(_, p43) --[[ Name: set_alpha ]] --[[ Line: 203 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_20 ]]
        if v_u_21 ~= p43 then
            v_u_21 = p43
            v_u_1:r_set_alpha(v_u_20, v_u_21)
        end;
    end;
    v19.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 209 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21;
    end;
    v19.set_scale = function(_, p44) --[[ Name: set_scale ]] --[[ Line: 210 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        v_u_22 = p44
    end;
    v19.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 211 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22;
    end;
    v19.get_native_size = function(p45) --[[ Name: get_native_size ]] --[[ Line: 213 ]]
        return p45._native_size;
    end;
    v19.get_size = function(p46) --[[ Name: get_size ]] --[[ Line: 216 ]]
        return p46._size;
    end;
    v19.set_size = function(p47, p48) --[[ Name: set_size ]] --[[ Line: 219 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        p47._size = p48
        v_u_20.PrimaryPart.Size = Vector3.new(p48.X, p48.Y, 0)
    end;
    v19.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 223 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20.PrimaryPart.Position;
    end;
    v19.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 226 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20.PrimaryPart.SurfaceGui;
    end;
    v19:cons()
    return v19;
end;
return v_u_15;
