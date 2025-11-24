-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:42 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_10 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.TradeLocalProtocol)
local v_u_12 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_13 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_14 = require(game.ReplicatedStorage.Lobby.Menus.ActivePlayerTradeUI)
local v_u_15 = {
    ["ListElement"] = {}
}
v_u_15.new = function(_, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_9, (copy 5): v_u_6, (copy 6): v_u_5, (copy 7): v_u_8, (copy 8): v_u_3, (copy 9): v_u_12, (copy 10): v_u_11, (copy 11): v_u_14, (copy 12): v_u_7, (copy 13): v_u_13, (copy 14): v_u_10, (copy 15): v_u_15 ]]
    local v19 = v_u_4:new(p_u_17, p_u_18)
    local l__trade_local_protocol_0 = p_u_16._trade_local_protocol
    local v_u_20 = nil
    local v_u_21 = 1
    local v_u_22 = 1
    local v_u_23 = v_u_2:new()
    local v_u_24 = 0
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = 0
    v19.cons = function(p_u_31) --[[ Name: cons ]] --[[ Line: 43 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_1, (ref 3): v_u_9, (ref 4): v_u_29, (copy 5): p_u_16, (ref 6): v_u_6, (ref 7): v_u_5, (copy 8): p_u_17, (copy 9): l__trade_local_protocol_0, (copy 10): p_u_18, (ref 11): v_u_8, (ref 12): v_u_27, (ref 13): v_u_28, (ref 14): v_u_25, (ref 15): v_u_26 ]]
        v_u_20 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.TradesUI:Clone()
        v_u_20.Name = v_u_1:gen_name(v_u_20.Name)
        v_u_20.Parent = v_u_9:get_world_ui_folder()
        p_u_31._native_size = v_u_20.PrimaryPart.Size
        p_u_31._size = p_u_31._native_size
        v_u_29 = v_u_20.PrimaryPart.SurfaceGui.Frame.LoadedFrame.EmptyText
        p_u_31:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(p_u_31, v_u_20.PrimaryPart, v_u_20.BackButtonSurface), p_u_17, function() --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): l__trade_local_protocol_0, (ref 2): p_u_18, (copy 3): p_u_31, (ref 4): p_u_16, (ref 5): v_u_8 ]]
            l__trade_local_protocol_0:stop()
            p_u_18:remove_menu(p_u_31)
            p_u_16._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
        end))
        v_u_27 = p_u_31:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(p_u_31, v_u_20.PrimaryPart, v_u_20.TradesButton), p_u_17, function() --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_8, (copy 3): p_u_31 ]]
            p_u_16._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_31:update_mode(1)
        end))
        v_u_28 = p_u_31:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(p_u_31, v_u_20.PrimaryPart, v_u_20.RequestsButton), p_u_17, function() --[[ Line: 75 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_8, (copy 3): p_u_31 ]]
            p_u_16._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_31:update_mode(2)
        end))
        v_u_25 = p_u_31:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(p_u_31, v_u_20.PrimaryPart, v_u_20.TopArrowSurface), p_u_17, function() --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_8, (copy 3): p_u_31 ]]
            p_u_16._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_31:offset_list_page(-1)
        end))
        v_u_26 = p_u_31:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(p_u_31, v_u_20.PrimaryPart, v_u_20.BottomArrowSurface), p_u_17, function() --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_8, (copy 3): p_u_31 ]]
            p_u_16._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_31:offset_list_page(1)
        end))
        p_u_31:setup_list_elements()
        l__trade_local_protocol_0:start()
        p_u_31:reset_selected_item()
        p_u_31:transition_update_visual(0)
        p_u_31:layout()
    end;
    v19.update_mode = function(p32, p33) --[[ Name: update_mode ]] --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_24, (copy 2): v_u_23, (ref 3): v_u_25, (ref 4): v_u_26, (ref 5): v_u_27, (ref 6): v_u_28, (ref 7): v_u_20, (ref 8): v_u_1, (ref 9): v_u_21, (ref 10): v_u_30 ]]
        v_u_24 = p33
        for v34, v35 in v_u_23:key_itr() do
            for v36 = 1, v35:count() do
                v35:get(v36):set_visible(v34 == v_u_24)
            end;
        end;
        if v_u_24 == 0 then
            v_u_25:set_visible(false)
            v_u_26:set_visible(false)
            v_u_27:set_visible(false)
            v_u_28:set_visible(false)
            v_u_20.PrimaryPart.SurfaceGui.Frame.LoadedFrame.Visible = false
            v_u_20.PrimaryPart.SurfaceGui.Frame.LoadingFrame.Visible = true
        else
            v_u_27:set_visible(true)
            v_u_28:set_visible(true)
            if v_u_24 == 1 then
                v_u_1:obj_set_alpha(v_u_27:get_part(), 1, v_u_21)
                v_u_1:obj_set_alpha(v_u_28:get_part(), 0.5, v_u_21)
            elseif v_u_24 == 2 then
                v_u_1:obj_set_alpha(v_u_27:get_part(), 0.5, v_u_21)
                v_u_1:obj_set_alpha(v_u_28:get_part(), 1, v_u_21)
            end;
            v_u_20.PrimaryPart.SurfaceGui.Frame.LoadedFrame.Visible = true
            v_u_20.PrimaryPart.SurfaceGui.Frame.LoadingFrame.Visible = false
            v_u_30 = 0
            p32:update_list()
        end;
    end;
    v19.update_list = function(_) --[[ Name: update_list ]] --[[ Line: 143 ]]
        --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_24, (ref 3): v_u_30, (ref 4): v_u_25, (copy 5): l__trade_local_protocol_0, (ref 6): v_u_29, (ref 7): v_u_26, (ref 8): v_u_3, (ref 9): v_u_1 ]]
        local v37 = v_u_23:list_of(v_u_24)
        if v37 == nil then
            return;
        else
            local v38 = v_u_30 * v37:count()
            v_u_25:set_visible(v38 > 0)
            if v_u_24 == 1 then
                local v39 = l__trade_local_protocol_0:get_received_requests_playerids_list()
                for v40 = 1, v37:count() do
                    local v41 = v37:get(v40)
                    local v42 = v38 + v40
                    if v42 <= v39:count() then
                        local v43 = v39:get(v42)
                        v41:set_data(v43)
                        v41:set_player_info(l__trade_local_protocol_0:playerid_to_username(v43), v43)
                        v41:set_visible(true)
                    else
                        v41:set_visible(false)
                    end;
                end;
                if v39:count() == 0 then
                    v_u_29.Visible = true
                    v_u_29.Text = "No incoming trade requests."
                else
                    v_u_29.Visible = false
                end;
                v_u_26:set_visible((v_u_30 + 1) * v37:count() < v39:count())
            elseif v_u_24 == 2 then
                local v44 = l__trade_local_protocol_0:get_available_playerid_to_did_send_request_dict()
                local v45 = v_u_3:new()
                for v46, _ in v44:key_itr() do
                    if v46 ~= v_u_1:get_local_userid() then
                        v45:push_back(v46)
                    end;
                end;
                v45:sort(function(p47, p48) --[[ Line: 180 ]]
                    --[[ Upvalues: (ref 1): l__trade_local_protocol_0 ]]
                    return string.lower(l__trade_local_protocol_0:playerid_to_username(p47)) < string.lower(l__trade_local_protocol_0:playerid_to_username(p48));
                end)
                for v49 = 1, v37:count() do
                    local v50 = v37:get(v49)
                    local v51 = v38 + v49
                    if v51 <= v45:count() then
                        local v52 = v45:get(v51)
                        v50:set_data(v52)
                        v50:set_player_info(l__trade_local_protocol_0:playerid_to_username(v52), v52)
                        v50:set_visible(true)
                        v50:set_button_visible(v44:get(v52) == false)
                    else
                        v50:set_visible(false)
                    end;
                end;
                if v45:count() == 0 then
                    v_u_29.Visible = true
                    v_u_29.Text = "No available players."
                else
                    v_u_29.Visible = false
                end;
                v_u_26:set_visible((v_u_30 + 1) * v37:count() < v45:count())
            end;
        end;
    end;
    v19.offset_list_page = function(p53, p54) --[[ Name: offset_list_page ]] --[[ Line: 207 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        v_u_30 = v_u_30 + p54
        p53:update_list()
    end;
    v19.accept_button_pressed = function(p_u_55, p56, _) --[[ Name: accept_button_pressed ]] --[[ Line: 212 ]]
        --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_12, (copy 3): p_u_16, (copy 4): p_u_17, (copy 5): l__trade_local_protocol_0, (ref 6): v_u_11 ]]
        local v_u_57 = nil
        v_u_57 = p_u_18:push_menu(v_u_12:new(p_u_16, p_u_17, p_u_18):set_text("Loading...", ""):set_close_button_visible(false):set_update_fn(function() --[[ Line: 218 ]]
            --[[ Upvalues: (ref 1): l__trade_local_protocol_0, (ref 2): v_u_11, (ref 3): p_u_18, (ref 4): v_u_57, (copy 5): p_u_55 ]]
            if l__trade_local_protocol_0:get_current_mode() == v_u_11.Mode.Error then
                p_u_18:remove_menu(v_u_57)
                p_u_55:handle_trade_local_protocol_errmsg()
            elseif l__trade_local_protocol_0:get_current_mode() == v_u_11.Mode.ActivePlayerTrade then
                p_u_18:remove_menu(v_u_57)
                p_u_55:handle_trade_local_protocol_start_playertrade()
            end;
        end))
        p_u_18:remove_menu(p_u_55)
        l__trade_local_protocol_0:accept_trade_request_from_playerid(p56)
    end;
    v19.handle_trade_local_protocol_errmsg = function(p58) --[[ Name: handle_trade_local_protocol_errmsg ]] --[[ Line: 233 ]]
        --[[ Upvalues: (copy 1): l__trade_local_protocol_0, (ref 2): v_u_11, (copy 3): p_u_18, (ref 4): v_u_12, (copy 5): p_u_16, (copy 6): p_u_17 ]]
        if l__trade_local_protocol_0:get_current_mode() == v_u_11.Mode.Error then
            l__trade_local_protocol_0:stop()
            p_u_18:remove_menu(p58)
            p_u_18:push_menu(v_u_12:new(p_u_16, p_u_17, p_u_18):set_text("Trade Failed", l__trade_local_protocol_0:get_errmsg()))
        end;
    end;
    v19.handle_trade_local_protocol_start_playertrade = function(p59) --[[ Name: handle_trade_local_protocol_start_playertrade ]] --[[ Line: 241 ]]
        --[[ Upvalues: (copy 1): l__trade_local_protocol_0, (ref 2): v_u_11, (copy 3): p_u_18, (ref 4): v_u_14, (copy 5): p_u_16, (copy 6): p_u_17, (ref 7): v_u_7 ]]
        if l__trade_local_protocol_0:get_current_mode() == v_u_11.Mode.ActivePlayerTrade then
            p_u_18:remove_menu(p59)
            p_u_18:push_menu(v_u_14:new(p_u_16, p_u_17, p_u_18))
        else
            l__trade_local_protocol_0:stop()
            v_u_7:errf("handle_trade_local_protocol_start_playertrade when mode(%d)", l__trade_local_protocol_0:get_current_mode())
        end;
    end;
    v19.send_button_pressed = function(_, p60, p61) --[[ Name: send_button_pressed ]] --[[ Line: 252 ]]
        --[[ Upvalues: (copy 1): l__trade_local_protocol_0 ]]
        l__trade_local_protocol_0:send_trade_request_to_playerid(p60)
        p61:set_button_visible(false)
    end;
    local l_NO_UPDATE_TIME_0 = v_u_11.NO_UPDATE_TIME
    v19.behaviour_update = function(p62, p63, _) --[[ Name: behaviour_update ]] --[[ Line: 258 ]]
        --[[ Upvalues: (copy 1): p_u_16, (copy 2): l__trade_local_protocol_0, (ref 3): l_NO_UPDATE_TIME_0, (ref 4): v_u_24, (ref 5): v_u_1, (ref 6): v_u_13, (ref 7): v_u_10, (ref 8): v_u_11 ]]
        p62:behaviour_update_base(p63, p_u_16)
        if l__trade_local_protocol_0:get_last_updated_time() ~= l_NO_UPDATE_TIME_0 then
            l_NO_UPDATE_TIME_0 = l__trade_local_protocol_0:get_last_updated_time()
            if v_u_24 == 0 then
                p62:update_mode(1)
            end;
            p62:update_list()
        end;
        if v_u_1:is_dev_build() and (v_u_13.ActivePlayerTradeUIDebug == true and p_u_16._input:control_just_pressed(v_u_10.KEY_DEBUG_1)) then
            l__trade_local_protocol_0:debug_start_active_player_trade()
        end;
        if l__trade_local_protocol_0:get_current_mode() == v_u_11.Mode.Error then
            p62:handle_trade_local_protocol_errmsg()
        elseif l__trade_local_protocol_0:get_current_mode() == v_u_11.Mode.ActivePlayerTrade then
            p62:handle_trade_local_protocol_start_playertrade()
        end;
    end;
    v19.setup_list_elements = function(p_u_64) --[[ Name: setup_list_elements ]] --[[ Line: 285 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_20, (ref 3): v_u_15, (ref 4): v_u_5, (ref 5): v_u_1, (copy 6): p_u_16, (ref 7): v_u_6, (copy 8): p_u_17, (ref 9): v_u_8, (copy 10): v_u_23, (ref 11): v_u_24 ]]
        local v_u_65 = v_u_3:new()
        for v66 = 1, 4 do
            v_u_65:push_back(v_u_20.Anchors:FindFirstChild(string.format("Anchor%d", v66)))
        end;
        local l_TradeRequestProto_0 = v_u_20.TradeRequestProto
        l_TradeRequestProto_0.Parent = nil
        for v_u_67 = 1, v_u_65:count() do
            local v_u_68 = l_TradeRequestProto_0:Clone()
            v_u_68.Parent = v_u_20
            v_u_23:push_back_to(1, ((function() --[[ Line: 298 ]]
                --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_5, (copy 3): p_u_64, (ref 4): v_u_20, (copy 5): v_u_68, (ref 6): v_u_1, (ref 7): p_u_16, (ref 8): v_u_6, (ref 9): p_u_17, (ref 10): v_u_8, (copy 11): v_u_65, (copy 12): v_u_67 ]]
                local v_u_69 = v_u_15.ListElement:new(v_u_5:new(p_u_64, v_u_20.PrimaryPart, v_u_68))
                local l_NameDisplay_0 = v_u_68.SurfaceGui.Frame.NameDisplay
                local l_Icon_0 = v_u_68.SurfaceGui.Frame.IconBack.Icon
                v_u_69.set_player_info = function(_, p70, p71) --[[ Name: set_player_info ]] --[[ Line: 303 ]]
                    --[[ Upvalues: (copy 1): l_NameDisplay_0, (ref 2): v_u_1, (copy 3): l_Icon_0 ]]
                    l_NameDisplay_0.Text = p70
                    v_u_1:get_user_thumbnail(p71, function(p72, _) --[[ Line: 305 ]]
                        --[[ Upvalues: (ref 1): l_Icon_0 ]]
                        if l_Icon_0 ~= nil then
                            l_Icon_0.Image = p72
                        end;
                    end, false)
                end;
                local v_u_73 = p_u_64:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(v_u_69:get_uichild(), v_u_68, v_u_68.AcceptButtonProto), p_u_17, function() --[[ Line: 313 ]]
                    --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_8, (ref 3): p_u_64, (copy 4): v_u_69 ]]
                    p_u_16._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                    p_u_64:accept_button_pressed(v_u_69:get_data(), v_u_69)
                end))
                v_u_69.set_visible = function(_, p74) --[[ Name: set_visible ]] --[[ Line: 319 ]]
                    --[[ Upvalues: (copy 1): v_u_69, (copy 2): v_u_73 ]]
                    v_u_69:set_visible_base(p74)
                    v_u_73:set_visible(p74)
                end;
                v_u_69:get_uichild():set_position(v_u_65:get(v_u_67).Position)
                v_u_69:set_visible(false)
                return v_u_69;
            end)()))
        end;
        local l_TradeSentProto_0 = v_u_20.TradeSentProto
        l_TradeSentProto_0.Parent = nil
        for v_u_75 = 1, v_u_65:count() do
            local v_u_76 = l_TradeSentProto_0:Clone()
            v_u_76.Parent = v_u_20
            v_u_23:push_back_to(2, ((function() --[[ Line: 339 ]]
                --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_5, (copy 3): p_u_64, (ref 4): v_u_20, (copy 5): v_u_76, (ref 6): v_u_1, (ref 7): p_u_16, (ref 8): v_u_6, (ref 9): p_u_17, (ref 10): v_u_8, (copy 11): v_u_65, (copy 12): v_u_75 ]]
                local v_u_77 = v_u_15.ListElement:new(v_u_5:new(p_u_64, v_u_20.PrimaryPart, v_u_76))
                local l_NameDisplay_1 = v_u_76.SurfaceGui.Frame.NameDisplay
                local l_Icon_1 = v_u_76.SurfaceGui.Frame.IconBack.Icon
                v_u_77.set_player_info = function(_, p78, p79) --[[ Name: set_player_info ]] --[[ Line: 344 ]]
                    --[[ Upvalues: (copy 1): l_NameDisplay_1, (ref 2): v_u_1, (copy 3): l_Icon_1 ]]
                    l_NameDisplay_1.Text = p78
                    v_u_1:get_user_thumbnail(p79, function(p80, _) --[[ Line: 346 ]]
                        --[[ Upvalues: (ref 1): l_Icon_1 ]]
                        if l_Icon_1 ~= nil then
                            l_Icon_1.Image = p80
                        end;
                    end, false)
                end;
                local v_u_81 = p_u_64:add_cycle_element(p_u_16, 1, v_u_6:new(v_u_5:new(v_u_77:get_uichild(), v_u_76, v_u_76.SendButtonProto), p_u_17, function() --[[ Line: 354 ]]
                    --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_8, (ref 3): p_u_64, (copy 4): v_u_77 ]]
                    p_u_16._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                    p_u_64:send_button_pressed(v_u_77:get_data(), v_u_77)
                end))
                v_u_77.set_button_visible = function(_, p82) --[[ Name: set_button_visible ]] --[[ Line: 360 ]]
                    --[[ Upvalues: (copy 1): v_u_81 ]]
                    v_u_81:set_visible(p82)
                end;
                v_u_77.set_visible = function(_, p83) --[[ Name: set_visible ]] --[[ Line: 364 ]]
                    --[[ Upvalues: (copy 1): v_u_77, (copy 2): v_u_81 ]]
                    v_u_77:set_visible_base(p83)
                    v_u_81:set_visible(p83)
                end;
                v_u_77:get_uichild():set_position(v_u_65:get(v_u_75).Position)
                v_u_77:set_visible(false)
                return v_u_77;
            end)()))
        end;
        p_u_64:update_mode(v_u_24)
    end;
    v19.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 380 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        v_u_20:Destroy()
    end;
    v19.layout = function(p84) --[[ Name: layout ]] --[[ Line: 384 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_22, (ref 3): v_u_20, (copy 4): v_u_23 ]]
        p84:opt_rescale_to_max_nxy(p_u_17, 0.88, 0.88, v_u_22)
        local v85, v86 = p84:opt_update_cframe_params(p_u_17, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p84:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v85 == true then
            v_u_20:SetPrimaryPartCFrame(v86)
        end;
        for _, v87 in v_u_23:key_itr() do
            for v88 = 1, v87:count() do
                v87:get(v88):layout()
            end;
        end;
    end;
    v19.set_alpha = function(_, p89) --[[ Name: set_alpha ]] --[[ Line: 402 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_20 ]]
        if v_u_21 ~= p89 then
            v_u_21 = p89
            v_u_1:r_set_alpha(v_u_20, v_u_21)
        end;
    end;
    v19.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 408 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21;
    end;
    v19.set_scale = function(_, p90) --[[ Name: set_scale ]] --[[ Line: 409 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        v_u_22 = p90
    end;
    v19.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 410 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22;
    end;
    v19.get_native_size = function(p91) --[[ Name: get_native_size ]] --[[ Line: 412 ]]
        return p91._native_size;
    end;
    v19.get_size = function(p92) --[[ Name: get_size ]] --[[ Line: 415 ]]
        return p92._size;
    end;
    v19.set_size = function(p93, p94) --[[ Name: set_size ]] --[[ Line: 418 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        p93._size = p94
        v_u_20.PrimaryPart.Size = Vector3.new(p94.X, p94.Y, 0)
    end;
    v19.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 422 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20.PrimaryPart.Position;
    end;
    v19.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 425 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20.PrimaryPart.SurfaceGui;
    end;
    v19:cons()
    return v19;
end;
v_u_15.ListElement.new = function(_, p_u_95) --[[ Name: new ]] --[[ Line: 434 ]]
    local v99 = {
        ["cons"] = function(p96) --[[ Name: cons ]] --[[ Line: 437 ]]
            p96:set_player_info("", 0)
        end,
        ["set_player_info"] = function(_, _, _) end,
        ["set_visible"] = function(p97, _) --[[ Name: set_visible ]] --[[ Line: 449 ]]
            p97:set_visible_base()
        end,
        ["layout"] = function(p98) --[[ Name: layout ]] --[[ Line: 454 ]]
            p98:layout_base()
        end
    }
    v99.get_uichild = function(_) --[[ Name: get_uichild ]] --[[ Line: 443 ]]
        --[[ Upvalues: (copy 1): p_u_95 ]]
        return p_u_95;
    end;
    local v_u_100 = nil
    v99.set_data = function(_, p101) --[[ Name: set_data ]] --[[ Line: 446 ]]
        --[[ Upvalues: (ref 1): v_u_100 ]]
        v_u_100 = p101
    end;
    v99.get_data = function(_) --[[ Name: get_data ]] --[[ Line: 447 ]]
        --[[ Upvalues: (ref 1): v_u_100 ]]
        return v_u_100;
    end;
    v99.set_visible_base = function(_, p102) --[[ Name: set_visible_base ]] --[[ Line: 450 ]]
        --[[ Upvalues: (copy 1): p_u_95 ]]
        p_u_95:get_child_part().SurfaceGui.Enabled = p102
    end;
    v99.layout_base = function(_) --[[ Name: layout_base ]] --[[ Line: 455 ]]
        --[[ Upvalues: (copy 1): p_u_95 ]]
        p_u_95:layout()
    end;
    v99:cons()
    return v99;
end;
return v_u_15;
