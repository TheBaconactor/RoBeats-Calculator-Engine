-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRect)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.SPChat.Local.SPChatWindowInputBar)
local v_u_9 = require(game.ReplicatedStorage.SPChat.Local.SPChatWindowTextButton)
local v_u_10 = require(game.ReplicatedStorage.SPChat.Local.SPChatWindowButtonControls)
return {
    ["new"] = function(_, p_u_11, p_u_12, p_u_13) --[[ Name: new ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1, (copy 3): v_u_9, (copy 4): v_u_10, (copy 5): v_u_8, (copy 6): v_u_7, (copy 7): v_u_2, (copy 8): v_u_4, (copy 9): v_u_5, (copy 10): v_u_3 ]]
        local v_u_14 = {}
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = v_u_6:new()
        local v_u_25 = v_u_6:new()
        local function f_cons() --[[ Name: cons ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_1, (ref 3): v_u_16, (ref 4): v_u_17, (ref 5): v_u_18, (ref 6): v_u_19, (ref 7): v_u_22, (ref 8): v_u_21, (copy 9): v_u_14, (ref 10): v_u_9, (copy 11): p_u_11, (copy 12): p_u_12, (ref 13): v_u_23, (ref 14): v_u_10, (ref 15): v_u_20, (ref 16): v_u_8 ]]
            v_u_15 = Instance.new("ScreenGui")
            v_u_15.Name = "SPChatWindow"
            v_u_15.ResetOnSpawn = false
            v_u_15.DisplayOrder = 0
            v_u_15.Parent = game.Players.LocalPlayer.PlayerGui
            v_u_1:ptry(function() --[[ Line: 42 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_15 ]]
                if v_u_1:do_disable_chat() then
                    v_u_15.Parent = nil
                end;
            end)
            v_u_16 = Instance.new("Frame")
            v_u_16.Parent = v_u_15
            v_u_16.Name = "BaseFrame"
            v_u_16.BackgroundColor3 = Color3.new(0, 0, 0)
            v_u_16.BackgroundTransparency = v_u_1:tra(0.4)
            v_u_16.Position = UDim2.new(0, 0, 0, -v_u_1:topbar_size())
            v_u_16.Active = true
            v_u_16.ZIndex = 0
            v_u_16.ClipsDescendants = true
            v_u_16.Size = UDim2.new(0, math.min(v_u_1:screen_size().X * 0.4, 450), 0, (math.min(v_u_1:screen_size().Y * 0.4, 250)))
            v_u_17 = Instance.new("Frame")
            v_u_17.Parent = v_u_16
            v_u_17.BackgroundTransparency = v_u_1:tra(0.5)
            v_u_17.Name = "MessageDisplayFrame"
            v_u_17.BackgroundColor3 = Color3.new(0, 0, 0)
            v_u_17.Position = UDim2.new(0, 0, 0, v_u_1:topbar_size())
            v_u_18 = Instance.new("Frame")
            v_u_18.Parent = v_u_16
            v_u_18.BackgroundTransparency = 1
            v_u_18.Name = "InputBarFrame"
            v_u_18.AnchorPoint = Vector2.new(1, 1)
            v_u_19 = Instance.new("ImageLabel")
            v_u_19.Name = "ChatResizerButton"
            v_u_19.Parent = v_u_16
            v_u_19.Image = ""
            v_u_19.BackgroundTransparency = 1
            v_u_19.BorderSizePixel = 0
            v_u_19.BackgroundColor3 = Color3.new(163, 162, 165)
            v_u_19.Size = UDim2.new(0, 40, 0, 40)
            v_u_19.Position = UDim2.new(1, 0, 1, 0)
            v_u_19.AnchorPoint = Vector2.new(1, 1)
            v_u_19.Image = "rbxassetid://261880743"
            v_u_19.ImageTransparency = v_u_1:tra(1)
            v_u_19.ZIndex = 1
            v_u_22 = Instance.new("Frame")
            v_u_22.Parent = v_u_16
            v_u_22.Name = "OverlayFrame"
            v_u_22.BackgroundTransparency = v_u_1:tra(0.5)
            v_u_22.BackgroundColor3 = Color3.new(0, 0, 0)
            v_u_22.Position = UDim2.new(0, 0, 0, v_u_1:topbar_size())
            v_u_22.ZIndex = 1
            v_u_22.Visible = false
            v_u_21 = v_u_14:add_update_alpha_obj(v_u_9:new(p_u_11, v_u_16):set_zindex(1):set_frame_size(UDim2.new(0, 50, 0, 40)):set_frame_anchor_point(Vector2.new(0, 1)):set_frame_alpha(0):set_font_size(18):set_text_size(UDim2.new(1, 0, 1, 0)):set_clicked_fn(function() --[[ Line: 105 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_14 ]]
                p_u_12:cycle_chat_window_selected_channel_id()
                v_u_14:update_current_channel_display()
            end))
            local l_UITextSizeConstraint_0 = Instance.new("UITextSizeConstraint")
            l_UITextSizeConstraint_0.Parent = v_u_21:get_text()
            l_UITextSizeConstraint_0.MinTextSize = 1
            l_UITextSizeConstraint_0.MaxTextSize = 18
            v_u_21:get_text().TextScaled = true
            v_u_23 = v_u_10:new(p_u_11, v_u_14)
            v_u_20 = v_u_14:add_update_alpha_obj(v_u_8:new(p_u_11, v_u_14, v_u_18))
            v_u_14:set_alpha(0)
            v_u_14:on_layout_changed()
        end;
        v_u_14.get_top_bar = function(_) --[[ Name: get_top_bar ]] --[[ Line: 126 ]]
            --[[ Upvalues: (copy 1): p_u_13 ]]
            return p_u_13;
        end;
        v_u_14.add_update_alpha_obj = function(_, p26) --[[ Name: add_update_alpha_obj ]] --[[ Line: 128 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_24, (copy 3): v_u_25 ]]
            v_u_7:is_function(p26.update)
            v_u_24:push_back(p26)
            v_u_7:is_function(p26.set_alpha)
            v_u_25:push_back(p26)
            return p26;
        end;
        v_u_14.update_current_channel_display = function(_) --[[ Name: update_current_channel_display ]] --[[ Line: 136 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_21, (ref 3): v_u_2 ]]
            local v27 = p_u_12:get_chat_window_selected_channel_id()
            local v28
            if v27 == nil then
                v28 = nil
            else
                v28 = p_u_12:get_channel(v27)
            end;
            if v28 == nil then
                v_u_21:set_frame_size(UDim2.new(0, 0, 0, 0))
                v_u_2:warnf("SPChatWindow:update_current_channel_display")
            else
                v_u_21:set_frame_size(UDim2.new(0, 50, 0, 40))
                v_u_21:set_text_message(v28:get_name())
                v_u_21:set_font_color(v28:get_color())
            end;
        end;
        v_u_14.get_visible = function(_) --[[ Name: get_visible ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15.Enabled;
        end;
        v_u_14.set_visible = function(_, p29) --[[ Name: set_visible ]] --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            v_u_15.Enabled = p29
        end;
        local v_u_30 = nil
        v_u_14.set_on_layout_changed_fn = function(_, p31) --[[ Name: set_on_layout_changed_fn ]] --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            v_u_30 = p31
        end;
        v_u_14.on_layout_changed = function(_) --[[ Name: on_layout_changed ]] --[[ Line: 163 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_16, (ref 3): v_u_18, (ref 4): v_u_20, (ref 5): v_u_17, (ref 6): v_u_1, (ref 7): v_u_22, (ref 8): v_u_30 ]]
            local l_X_0 = v_u_21:get_frame_absolute_size().X
            v_u_21:set_frame_position(UDim2.new(0, 0, 0, v_u_16.AbsoluteSize.Y))
            v_u_18.Position = UDim2.new(0, v_u_16.AbsoluteSize.X - 40, 0, v_u_16.AbsoluteSize.Y)
            v_u_18.Size = UDim2.new(0, v_u_16.AbsoluteSize.X - 40 - l_X_0, 0, v_u_18.Size.Y.Offset)
            v_u_20:fit_to_text()
            v_u_17.Size = UDim2.new(0, v_u_16.AbsoluteSize.X, 0, v_u_16.AbsoluteSize.Y - v_u_1:topbar_size() - v_u_20:get_height())
            v_u_22.Size = v_u_17.Size
            if v_u_30 then
                v_u_30()
            end;
        end;
        v_u_14.get_message_display_frame = function(_) --[[ Name: get_message_display_frame ]] --[[ Line: 184 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17;
        end;
        local v_u_32 = v_u_6:new()
        v_u_14.register_on_text_sent_fn = function(_, p33) --[[ Name: register_on_text_sent_fn ]] --[[ Line: 187 ]]
            --[[ Upvalues: (copy 1): v_u_32 ]]
            v_u_32:push_back(p33)
        end;
        local v_u_34 = ""
        local v_u_35 = v_u_6:new()
        v_u_14.register_on_text_changed_fn = function(_, p36) --[[ Name: register_on_text_changed_fn ]] --[[ Line: 193 ]]
            --[[ Upvalues: (copy 1): v_u_35 ]]
            v_u_35:push_back(p36)
        end;
        v_u_4:new()
        v_u_14.update = function(p37, p38) --[[ Name: update ]] --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): v_u_23, (copy 2): v_u_24, (ref 3): v_u_20, (copy 4): v_u_32, (ref 5): v_u_34, (copy 6): v_u_35 ]]
            p37:update_resize(p38)
            v_u_23:update(p38)
            for v39 = 1, v_u_24:count() do
                v_u_24:get(v39):update(p38)
            end;
            local v40, v41 = v_u_20:test_text_sent()
            if v40 then
                for v42 = 1, v_u_32:count() do
                    v_u_32:get(v42)(v41)
                end;
            end;
            local v43 = v_u_20:get_current_text()
            if v43 ~= v_u_34 then
                for v44 = 1, v_u_35:count() do
                    v_u_35:get(v44)(v43)
                end;
                v_u_34 = v43
            end;
        end;
        local v_u_45 = -1
        v_u_14.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): v_u_45 ]]
            return v_u_45;
        end;
        v_u_14.set_alpha = function(_, p46) --[[ Name: set_alpha ]] --[[ Line: 226 ]]
            --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_16, (ref 3): v_u_1, (ref 4): v_u_5, (ref 5): v_u_17, (ref 6): v_u_19, (copy 7): v_u_25 ]]
            if p46 ~= v_u_45 then
                v_u_45 = p46
                v_u_16.BackgroundTransparency = v_u_1:tra(v_u_5:Lerp(0, 0.4, v_u_45))
                v_u_17.BackgroundTransparency = v_u_1:tra(v_u_5:Lerp(0, 0.5, v_u_45))
                v_u_19.ImageTransparency = v_u_1:tra(v_u_5:Lerp(0, 1, v_u_45))
                for v47 = 1, v_u_25:count() do
                    v_u_25:get(v47):set_alpha(v_u_45)
                end;
            end;
        end;
        local v_u_48 = false
        local v_u_49 = Vector2.new()
        local v_u_50 = v_u_4:new()
        local v_u_51 = v_u_4:new()
        v_u_14.update_resize = function(p52, p53) --[[ Name: update_resize ]] --[[ Line: 242 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_16, (copy 3): v_u_51, (ref 4): v_u_19, (copy 5): v_u_50, (copy 6): p_u_11, (ref 7): v_u_3, (ref 8): v_u_48, (ref 9): v_u_49, (ref 10): v_u_45, (ref 11): v_u_5 ]]
            local v54 = v_u_1:get_cursor_nxy()
            v_u_1:get_ui_object_nrect(v_u_16, v_u_51)
            v_u_1:get_ui_object_nrect(v_u_19, v_u_50)
            if p_u_11._input:control_just_pressed(v_u_3.KEY_CLICK) then
                if v_u_50:contains_vec2(v54) then
                    v_u_48 = true
                    local v55 = v_u_51:pt2() - v54
                    v_u_49 = Vector2.new(v55.X * v_u_1:screen_size().X, v55.Y * v_u_1:screen_size().Y)
                end;
            elseif p_u_11._input:control_pressed(v_u_3.KEY_CLICK) ~= true and v_u_48 == true then
                p52:on_layout_changed()
                v_u_48 = false
            end;
            if v_u_48 then
                local v56, v57 = v_u_1:nxy_to_nontopbar_screen_pos(v54.X, v54.Y)
                local v58 = Vector2.new(v56, v57) + v_u_49 - Vector2.new(v_u_16.AbsolutePosition.X, v_u_16.AbsolutePosition.Y)
                v_u_16.Size = UDim2.new(0, v_u_1:clamp(v58.X, 50, v_u_1:screen_size().X), 0, v_u_1:clamp(v58.Y, v_u_1:topbar_size() + 40 + 10, v_u_1:screen_size().Y))
                v_u_16.ZIndex = 20
                v_u_19.ZIndex = 21
            else
                v_u_16.ZIndex = 0
                v_u_19.ZIndex = 1
            end;
            local v59
            if v_u_50:contains_vec2(v54) then
                if v_u_48 == true then
                    v59 = v_u_45 * 0.15
                else
                    v59 = v_u_45 * 0.05
                end;
            else
                v59 = 0
            end;
            v_u_19.BackgroundTransparency = v_u_1:tra(v_u_5:expt_sec(v_u_1:tra(v_u_19.BackgroundTransparency), v59, 0.25, p53))
        end;
        v_u_14.get_base_frame = function(_) --[[ Name: get_base_frame ]] --[[ Line: 295 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            return v_u_16;
        end;
        v_u_14.get_overlay_frame = function(_) --[[ Name: get_overlay_frame ]] --[[ Line: 296 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        v_u_14.get_parent_adapter = function(_) --[[ Name: get_parent_adapter ]] --[[ Line: 297 ]]
            --[[ Upvalues: (copy 1): p_u_12 ]]
            return p_u_12;
        end;
        local v_u_60 = v_u_4:new()
        v_u_14.get_base_frame_nrect = function(p61) --[[ Name: get_base_frame_nrect ]] --[[ Line: 300 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1, (copy 3): v_u_60 ]]
            if p61:get_visible() == true then
                return v_u_1:get_ui_object_nrect(p61:get_base_frame(), v_u_60);
            else
                return v_u_4.ZERO;
            end;
        end;
        v_u_14.get_input_bar = function(_) --[[ Name: get_input_bar ]] --[[ Line: 305 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        f_cons()
        return v_u_14;
    end
};
