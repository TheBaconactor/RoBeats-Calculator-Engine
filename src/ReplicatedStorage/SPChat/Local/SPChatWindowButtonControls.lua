-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRect)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.SPChat.Local.SPChatWindowTextButton)
local v7 = {}
local v_u_8 = {
    ["Hidden"] = 0,
    ["FilterList"] = 1,
    ["InvitePlayerList"] = 2,
    ["LeaveChannelList"] = 3
}
local v_u_15 = {
    ["new"] = function(_, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13) --[[ Name: new ]] --[[ Line: 25 ]]
        local v14 = {}
        v14.get_message_frame = function(_) --[[ Name: get_message_frame ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): p_u_9 ]]
            return p_u_9;
        end;
        v14.get_message_text = function(_) --[[ Name: get_message_text ]] --[[ Line: 28 ]]
            --[[ Upvalues: (copy 1): p_u_10 ]]
            return p_u_10;
        end;
        v14.get_message_image = function(_) --[[ Name: get_message_image ]] --[[ Line: 29 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            return p_u_11;
        end;
        v14.get_test_show_check_fn = function(_) --[[ Name: get_test_show_check_fn ]] --[[ Line: 30 ]]
            --[[ Upvalues: (copy 1): p_u_12 ]]
            return p_u_12;
        end;
        v14.get_on_toggle_fn = function(_) --[[ Name: get_on_toggle_fn ]] --[[ Line: 31 ]]
            --[[ Upvalues: (copy 1): p_u_13 ]]
            return p_u_13;
        end;
        return v14;
    end
}
v7.new = function(_, p_u_16, p_u_17) --[[ Name: new ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_6, (copy 3): v_u_1, (copy 4): v_u_3, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_15, (copy 8): v_u_2 ]]
    local v18 = {}
    local v_u_19 = nil
    local l_Hidden_0 = v_u_8.Hidden
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    v18.cons = function(p_u_23) --[[ Name: cons ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_17, (ref 3): v_u_20, (ref 4): v_u_6, (copy 5): p_u_16, (ref 6): v_u_1, (ref 7): l_Hidden_0, (ref 8): v_u_8, (ref 9): v_u_21, (ref 10): v_u_3, (ref 11): v_u_5, (ref 12): v_u_4, (ref 13): v_u_22 ]]
        v_u_19 = Instance.new("ScrollingFrame")
        v_u_19.Selectable = false
        v_u_19.Name = "Scroller"
        v_u_19.BackgroundTransparency = 1
        v_u_19.BorderSizePixel = 0
        v_u_19.Position = UDim2.new(0, 0, 0, 3)
        v_u_19.Size = UDim2.new(1, -4, 1, -6)
        v_u_19.CanvasSize = UDim2.new(0, 0, 0, 0)
        v_u_19.ScrollBarThickness = 4
        v_u_19.ScrollingDirection = Enum.ScrollingDirection.Y
        v_u_19.Active = false
        v_u_19.Parent = p_u_17:get_overlay_frame()
        v_u_19.ZIndex = 2
        v_u_20 = p_u_17:add_update_alpha_obj(v_u_6:new(p_u_16, p_u_17:get_base_frame()):set_zindex(1):set_update_fn(function() --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_1, (ref 3): v_u_20 ]]
            local v24 = p_u_17:get_top_bar()
            v_u_20:set_frame_position(UDim2.new(0, v24:get_frame_absolute_position().X + v24:get_frame_absolute_size().X + 6, 0, v_u_1:topbar_size() - 37))
        end):set_frame_color(v_u_1:color3(0, 0, 0)):set_frame_size(UDim2.new(0, 46.25, 0, 37)):set_frame_alpha(0.25):set_font_size(14):set_text_position(UDim2.new(0, 3, 0, 3)):set_text_size(UDim2.new(1, -6, 1, -6)):set_font_color(v_u_1:color3(255, 255, 255)):set_text_message("Visible\nChannels"):set_clicked_fn(function() --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_8, (copy 3): p_u_23, (ref 4): p_u_17 ]]
            if l_Hidden_0 == v_u_8.FilterList then
                l_Hidden_0 = v_u_8.Hidden
            else
                l_Hidden_0 = v_u_8.FilterList
                p_u_23:clear_list_elements()
                p_u_23:add_list_header("Set Visible Chat Channels")
                for v_u_25, v26 in p_u_17:get_parent_adapter():channels_itr() do
                    p_u_23:add_list_element(v26:get_name(), function() --[[ Line: 90 ]]
                        --[[ Upvalues: (ref 1): p_u_17, (copy 2): v_u_25 ]]
                        return p_u_17:get_parent_adapter():get_id_to_channel_visible(v_u_25);
                    end, function() --[[ Line: 91 ]]
                        --[[ Upvalues: (ref 1): p_u_17, (copy 2): v_u_25 ]]
                        p_u_17:get_parent_adapter():set_id_to_channel_visible(v_u_25, not p_u_17:get_parent_adapter():get_id_to_channel_visible(v_u_25))
                    end)
                end;
            end;
            p_u_23:update_overlay_list_mode()
        end))
        v_u_21 = p_u_17:add_update_alpha_obj(v_u_6:new(p_u_16, p_u_17:get_base_frame()):set_zindex(1):set_update_fn(function() --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_1, (ref 3): v_u_21 ]]
            local v27 = p_u_17:get_top_bar()
            v_u_21:set_frame_position(UDim2.new(0, v27:get_frame_absolute_position().X + v27:get_frame_absolute_size().X + 6 + 57, 0, v_u_1:topbar_size() - 37))
        end):set_frame_color(v_u_1:color3(0, 0, 0)):set_frame_size(UDim2.new(0, 46.25, 0, 37)):set_frame_alpha(0.25):set_font_size(14):set_text_position(UDim2.new(0, 3, 0, 3)):set_text_size(UDim2.new(1, -6, 1, -6)):set_font_color(v_u_1:color3(255, 255, 255)):set_text_message("-"):set_clicked_fn(function() --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): l_Hidden_0, (ref 3): v_u_8, (copy 4): p_u_23, (ref 5): v_u_3, (ref 6): v_u_5, (ref 7): v_u_1, (ref 8): v_u_4 ]]
            if p_u_16._chat:can_request_custom_channel() then
                p_u_16._chat:request_custom_channel()
            elseif p_u_16._chat:has_custom_channel() then
                if l_Hidden_0 == v_u_8.InvitePlayerList then
                    l_Hidden_0 = v_u_8.Hidden
                else
                    l_Hidden_0 = v_u_8.InvitePlayerList
                    p_u_23:clear_list_elements()
                    p_u_23:add_list_header("Invite Players to your Private Chat Channel")
                    local v28 = v_u_3:new()
                    for _, v29 in pairs(game.Players:GetPlayers()) do
                        v28:push_back(v29)
                    end;
                    v28:sort(function(p30, p31) --[[ Line: 130 ]]
                        return string.lower(p30.Name) < string.lower(p31.Name);
                    end)
                    for _, v_u_32 in v28:key_itr() do
                        if v_u_5.CanSendChannelInviteToSelf == true and true or v_u_32 ~= v_u_1:get_local_player() then
                            local v_u_33 = false
                            p_u_23:add_list_element(v_u_32.Name, function() --[[ Line: 146 ]]
                                --[[ Upvalues: (ref 1): v_u_33 ]]
                                return v_u_33;
                            end, function() --[[ Line: 147 ]]
                                --[[ Upvalues: (ref 1): v_u_33, (ref 2): p_u_16, (ref 3): v_u_4, (copy 4): v_u_32 ]]
                                if v_u_33 ~= true then
                                    v_u_33 = true
                                    p_u_16._evt:fire_event_to_server(v_u_4.EVT_Chat_SendPlayerCustomChannelInvite, v_u_32.UserId)
                                end;
                            end)
                        end;
                    end;
                end;
                p_u_23:update_overlay_list_mode()
            end;
        end))
        v_u_22 = p_u_17:add_update_alpha_obj(v_u_6:new(p_u_16, p_u_17:get_base_frame()):set_zindex(1):set_update_fn(function() --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_1, (ref 3): v_u_22 ]]
            local v34 = p_u_17:get_top_bar()
            v_u_22:set_frame_position(UDim2.new(0, v34:get_frame_absolute_position().X + v34:get_frame_absolute_size().X + 6 + 114, 0, v_u_1:topbar_size() - 37))
        end):set_frame_color(v_u_1:color3(0, 0, 0)):set_frame_size(UDim2.new(0, 46.25, 0, 37)):set_frame_alpha(0.25):set_font_size(14):set_text_position(UDim2.new(0, 3, 0, 3)):set_text_size(UDim2.new(1, -6, 1, -6)):set_font_color(v_u_1:color3(255, 255, 255)):set_text_message("Leave\nChannel"):set_clicked_fn(function() --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_8, (copy 3): p_u_23, (ref 4): p_u_17, (ref 5): p_u_16, (ref 6): v_u_4 ]]
            if l_Hidden_0 == v_u_8.LeaveChannelList then
                l_Hidden_0 = v_u_8.Hidden
            else
                l_Hidden_0 = v_u_8.LeaveChannelList
                p_u_23:clear_list_elements()
                p_u_23:add_list_header("Leave Channel")
                for v_u_35, v36 in p_u_17:get_parent_adapter():channels_itr() do
                    if p_u_16._chat:get_joined_custom_channels():contains(v_u_35) then
                        p_u_23:add_list_element(v36:get_name(), function() --[[ Line: 189 ]]
                            return false;
                        end, function() --[[ Line: 190 ]]
                            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_4, (copy 3): v_u_35, (ref 4): l_Hidden_0, (ref 5): v_u_8, (ref 6): p_u_23 ]]
                            p_u_16._evt:fire_event_to_server(v_u_4.EVT_Chat_ClientLeaveCustomChannel, v_u_35)
                            l_Hidden_0 = v_u_8.Hidden
                            p_u_23:update_overlay_list_mode()
                        end)
                    end;
                end;
            end;
            p_u_23:update_overlay_list_mode()
        end))
    end;
    local v_u_37 = v_u_3:new()
    local v_u_38 = 0
    v18.clear_list_elements = function(_) --[[ Name: clear_list_elements ]] --[[ Line: 206 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_38, (copy 3): v_u_37 ]]
        for _, v39 in pairs(v_u_19:GetChildren()) do
            v39:Destroy()
        end;
        v_u_38 = 0
        v_u_19.CanvasSize = UDim2.new(0, 0, 0, 0)
        v_u_37:clear()
    end;
    local function f_create_list_display_element() --[[ Name: create_list_display_element ]] --[[ Line: 215 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_19, (ref 3): v_u_38 ]]
        local l_Frame_0 = Instance.new("Frame")
        l_Frame_0.Selectable = false
        l_Frame_0.Size = UDim2.new(1, 0, 0, 18)
        l_Frame_0.Visible = true
        l_Frame_0.BackgroundColor3 = v_u_1:color3(255, 255, 255)
        l_Frame_0.BackgroundTransparency = 1
        l_Frame_0.ZIndex = 3
        l_Frame_0.Parent = v_u_19
        l_Frame_0.Position = UDim2.new(0, 0, 0, v_u_38)
        v_u_38 = v_u_38 + l_Frame_0.Size.Y.Offset
        v_u_19.CanvasSize = UDim2.new(0, 0, 0, v_u_38)
        local l_TextLabel_0 = Instance.new("TextLabel")
        l_TextLabel_0.BackgroundTransparency = 1
        l_TextLabel_0.Selectable = false
        l_TextLabel_0.Font = Enum.Font.SourceSansBold
        l_TextLabel_0.TextSize = 18
        l_TextLabel_0.TextXAlignment = Enum.TextXAlignment.Left
        l_TextLabel_0.TextYAlignment = Enum.TextYAlignment.Top
        l_TextLabel_0.TextTransparency = 0
        l_TextLabel_0.TextStrokeTransparency = 0.75
        l_TextLabel_0.TextColor3 = v_u_1:color3(255, 255, 255)
        l_TextLabel_0.Visible = true
        l_TextLabel_0.Parent = l_Frame_0
        l_TextLabel_0.ZIndex = 4
        l_TextLabel_0.AutoLocalize = false
        l_TextLabel_0.Position = UDim2.new(0, 18, 0, 0)
        l_TextLabel_0.Size = UDim2.new(1, -18, 1, 0)
        local l_ImageLabel_0 = Instance.new("ImageLabel")
        l_ImageLabel_0.BackgroundTransparency = 1
        l_ImageLabel_0.ImageTransparency = 0
        l_ImageLabel_0.Image = v_u_1:get_miniqueue_ready_assetid()
        l_ImageLabel_0.AutoLocalize = false
        l_ImageLabel_0.Parent = l_Frame_0
        l_ImageLabel_0.ZIndex = 4
        l_ImageLabel_0.Visible = false
        l_ImageLabel_0.Size = UDim2.new(0, 18, 0, 18)
        return l_Frame_0, l_TextLabel_0, l_ImageLabel_0;
    end;
    v18.add_list_header = function(_, p40) --[[ Name: add_list_header ]] --[[ Line: 258 ]]
        --[[ Upvalues: (copy 1): f_create_list_display_element ]]
        local _, v41, v42 = f_create_list_display_element()
        v41.TextXAlignment = Enum.TextXAlignment.Center
        v41.Text = p40
        v41.Position = UDim2.new(0, 0, 0, 0)
        v41.Size = UDim2.new(1, 0, 1, 0)
        v42.Visible = false
    end;
    v18.add_list_element = function(_, p43, p44, p45) --[[ Name: add_list_element ]] --[[ Line: 267 ]]
        --[[ Upvalues: (copy 1): f_create_list_display_element, (copy 2): v_u_37, (ref 3): v_u_15 ]]
        local v46, v47, v48 = f_create_list_display_element()
        v47.Text = p43
        v48.Visible = p44()
        v_u_37:push_back(v_u_15:new(v46, v47, v48, p44, p45))
    end;
    local v_u_49 = v_u_2:new()
    local v_u_50 = v_u_2:new()
    v18.update = function(p51, _) --[[ Name: update ]] --[[ Line: 276 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_37, (copy 3): v_u_49, (copy 4): p_u_17, (copy 5): v_u_50, (copy 6): p_u_16, (ref 7): v_u_21, (ref 8): l_Hidden_0, (ref 9): v_u_8, (ref 10): v_u_22 ]]
        local v52 = v_u_1:get_cursor_nxy()
        for v53 = 1, v_u_37:count() do
            local v54 = v_u_37:get(v53)
            if v54 == nil then
                break;
            end;
            v_u_1:get_ui_object_nrect(v54:get_message_frame(), v_u_49)
            v_u_1:get_ui_object_nrect(p_u_17:get_message_display_frame(), v_u_50)
            if v_u_50:contains_vec2(v52) and v_u_49:contains_vec2(v52) then
                v54:get_message_frame().BackgroundTransparency = 0.85
                if p_u_16._chat:do_press_trigger() then
                    v54:get_on_toggle_fn()()
                    v54:get_message_image().Visible = v54:get_test_show_check_fn()()
                end;
            else
                v54:get_message_frame().BackgroundTransparency = 1
            end;
        end;
        if p_u_16._chat:can_request_custom_channel() then
            v_u_21:set_text_message("Private\nChannel")
        elseif p_u_16._chat:has_custom_channel() == true then
            v_u_21:set_text_message("Invite\nPlayers")
        else
            v_u_21:set_text_message("Loading...")
        end;
        if l_Hidden_0 ~= v_u_8.Hidden and p_u_17:get_alpha() < 1 then
            l_Hidden_0 = v_u_8.Hidden
            p51:update_overlay_list_mode()
        end;
        if p_u_16._chat:get_joined_custom_channels():count() > 0 then
            v_u_22:set_visible(true)
        else
            v_u_22:set_visible(false)
        end;
    end;
    local function _(p55) --[[ Name: set_button_state_selected ]] --[[ Line: 314 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        p55:set_frame_color(v_u_1:color3(255, 255, 255))
    end;
    local function _(p56) --[[ Name: set_button_state_unselected ]] --[[ Line: 318 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        p56:set_frame_color(v_u_1:color3(0, 0, 0))
    end;
    v18.update_overlay_list_mode = function(p57) --[[ Name: update_overlay_list_mode ]] --[[ Line: 322 ]]
        --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_8, (copy 3): p_u_17, (ref 4): v_u_20, (ref 5): v_u_1, (ref 6): v_u_21, (ref 7): v_u_22 ]]
        if l_Hidden_0 == v_u_8.Hidden then
            p57:clear_list_elements()
            p_u_17:get_overlay_frame().Visible = false
            p_u_17:get_message_display_frame().Visible = true
            v_u_20:set_frame_color(v_u_1:color3(0, 0, 0))
            v_u_21:set_frame_color(v_u_1:color3(0, 0, 0))
            v_u_22:set_frame_color(v_u_1:color3(0, 0, 0))
            return;
        elseif l_Hidden_0 == v_u_8.FilterList then
            p_u_17:get_overlay_frame().Visible = true
            p_u_17:get_message_display_frame().Visible = false
            v_u_20:set_frame_color(v_u_1:color3(255, 255, 255))
            v_u_21:set_frame_color(v_u_1:color3(0, 0, 0))
            v_u_22:set_frame_color(v_u_1:color3(0, 0, 0))
            return;
        elseif l_Hidden_0 == v_u_8.InvitePlayerList then
            p_u_17:get_overlay_frame().Visible = true
            p_u_17:get_message_display_frame().Visible = false
            v_u_20:set_frame_color(v_u_1:color3(0, 0, 0))
            v_u_21:set_frame_color(v_u_1:color3(255, 255, 255))
            v_u_22:set_frame_color(v_u_1:color3(0, 0, 0))
        elseif l_Hidden_0 == v_u_8.LeaveChannelList then
            p_u_17:get_overlay_frame().Visible = true
            p_u_17:get_message_display_frame().Visible = false
            v_u_20:set_frame_color(v_u_1:color3(0, 0, 0))
            v_u_21:set_frame_color(v_u_1:color3(0, 0, 0))
            v_u_22:set_frame_color(v_u_1:color3(255, 255, 255))
        end;
    end;
    v18:cons()
    return v18;
end;
return v7;
