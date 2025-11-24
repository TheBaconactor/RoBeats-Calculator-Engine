-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.TextSizeCache)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.InputUtil)
return {
    ["new"] = function(_, p_u_5, p_u_6, p_u_7) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_1, (copy 4): v_u_2 ]]
        local v_u_8 = {}
        local v_u_9 = nil
        local v_u_10 = nil
        local v_u_11 = nil
        local v_u_12 = nil
        local l_Offset_0 = p_u_7.Size.Y.Offset
        local v_u_13 = l_Offset_0
        local v_u_14 = false
        local v_u_15 = ""
        v_u_8.get_current_text = function(_) --[[ Name: get_current_text ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_7, (ref 3): v_u_10, (ref 4): v_u_3, (ref 5): v_u_11, (ref 6): v_u_12, (copy 7): v_u_8, (ref 8): v_u_15 ]]
            v_u_9 = Instance.new("ScrollingFrame")
            v_u_9.Selectable = false
            v_u_9.Name = "BackgroundScrollingFrame"
            v_u_9.BorderSizePixel = 0
            v_u_9.Size = UDim2.new(1, -12, 1, -12)
            v_u_9.Position = UDim2.new(0, 6, 0, 6)
            v_u_9.ScrollBarThickness = 4
            v_u_9.Parent = p_u_7
            v_u_9.ScrollingDirection = Enum.ScrollingDirection.Y
            v_u_9.ZIndex = 2
            v_u_9.CanvasSize = UDim2.new(0, 0, 0, 0)
            v_u_9.CanvasPosition = Vector2.new(0, 0)
            v_u_9.BackgroundTransparency = 1
            v_u_10 = Instance.new("Frame")
            v_u_10.Selectable = false
            v_u_10.Name = "BackgroundFrame"
            v_u_10.BorderSizePixel = 0
            v_u_10.Size = v_u_9.Size
            v_u_10.Position = v_u_9.Position
            v_u_10.BackgroundTransparency = v_u_3:tra(0.4)
            v_u_10.BackgroundColor3 = Color3.new(1, 1, 1)
            v_u_10.Parent = p_u_7
            local l_Frame_0 = Instance.new("Frame")
            l_Frame_0.Name = "TextHolderFrame"
            l_Frame_0.BackgroundTransparency = 1
            l_Frame_0.Size = UDim2.new(1, -10, 1, -10)
            l_Frame_0.Position = UDim2.new(0, 5, 0, 5)
            l_Frame_0.Parent = v_u_9
            v_u_11 = Instance.new("TextBox")
            v_u_11.Selectable = false
            v_u_11.Name = "InputBox"
            v_u_11.BackgroundTransparency = 1
            v_u_11.Position = UDim2.new(0, 0, 0, 0)
            v_u_11.Size = UDim2.new(1, 0, 0, l_Frame_0.AbsoluteSize.Y)
            v_u_11.TextSize = 18
            v_u_11.Font = Enum.Font.SourceSansBold
            v_u_11.TextColor3 = Color3.new(0, 0, 0)
            v_u_11.TextTransparency = v_u_3:tra(0.6)
            v_u_11.TextStrokeTransparency = 1
            v_u_11.ClearTextOnFocus = false
            v_u_11.TextXAlignment = Enum.TextXAlignment.Left
            v_u_11.TextYAlignment = Enum.TextYAlignment.Top
            v_u_11.TextWrapped = true
            v_u_11.Text = ""
            v_u_11.Parent = l_Frame_0
            v_u_11.ZIndex = 4
            v_u_11.AutoLocalize = false
            v_u_11.Selectable = true
            v_u_12 = Instance.new("TextLabel")
            v_u_12.Name = "InputTextDisplay"
            v_u_12.Selectable = false
            v_u_12.TextWrapped = true
            v_u_12.BackgroundTransparency = 1
            v_u_12.Size = v_u_11.Size
            v_u_12.Position = v_u_11.Position
            v_u_12.TextSize = v_u_11.TextSize
            v_u_12.Font = v_u_11.Font
            v_u_12.TextColor3 = v_u_11.TextColor3
            v_u_12.TextTransparency = v_u_11.TextTransparency
            v_u_12.TextStrokeTransparency = v_u_11.TextStrokeTransparency
            v_u_12.TextXAlignment = v_u_11.TextXAlignment
            v_u_12.TextYAlignment = v_u_11.TextYAlignment
            v_u_12.Text = ""
            v_u_12.Parent = l_Frame_0
            v_u_12.ZIndex = 3
            v_u_12.Visible = false
            v_u_12.AutoLocalize = false
            if v_u_3:do_disable_chat() then
                v_u_11.Parent = nil
                v_u_12.Parent = nil
                l_Frame_0.Parent = nil
                v_u_10.Parent = nil
            end;
            v_u_11.Changed:Connect(function(p16) --[[ Line: 116 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_15, (ref 3): v_u_11 ]]
                local v17 = p16 == "Text"
                if v17 or p16 == "Size" then
                    v_u_8:fit_to_text()
                end;
                if v17 then
                    v_u_15 = v_u_11.Text
                end;
            end)
            v_u_11.Focused:connect(function() --[[ Line: 127 ]]
                --[[ Upvalues: (ref 1): v_u_8 ]]
                v_u_8:update_focus_state_changed(true)
            end)
            v_u_11.FocusLost:connect(function(p18, _) --[[ Line: 131 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_8 ]]
                if p18 and #v_u_11.Text > 0 then
                    v_u_8:raise_text_sent(v_u_11.Text)
                end;
                v_u_8:update_focus_state_changed(false)
            end)
            v_u_8:update_focus_state_changed(false)
        end;
        v_u_8.set_text_and_move_cursor_to_end = function(_, p19) --[[ Name: set_text_and_move_cursor_to_end ]] --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11.Text = p19
            v_u_11.CursorPosition = #p19 + 1
        end;
        local v_u_20 = ""
        local v_u_21 = false
        v_u_8.raise_text_sent = function(_, p22) --[[ Name: raise_text_sent ]] --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_20 ]]
            v_u_21 = true
            v_u_20 = p22
        end;
        v_u_8.test_text_sent = function(_) --[[ Name: test_text_sent ]] --[[ Line: 153 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_20 ]]
            local v23 = v_u_21
            v_u_21 = false
            return v23, v_u_20;
        end;
        v_u_8.clear = function(p24) --[[ Name: clear ]] --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11.Text = ""
            p24:update_focus_state_changed(false)
        end;
        local v_u_25 = false
        v_u_8.is_focused = function(_) --[[ Name: is_focused ]] --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            return v_u_25;
        end;
        v_u_8.update_focus_state_changed = function(_, p26) --[[ Name: update_focus_state_changed ]] --[[ Line: 167 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_12, (ref 3): v_u_9, (ref 4): v_u_11, (ref 5): v_u_3, (copy 6): p_u_5, (ref 7): v_u_4 ]]
            v_u_25 = p26
            if v_u_25 == true then
                v_u_12.Visible = false
                v_u_9.ZIndex = 5
            else
                if #v_u_11.Text == 0 then
                    if v_u_3:is_mobile() then
                        v_u_12.Text = "Tap here to chat"
                    else
                        v_u_12.Text = string.format("To chat click here or press \"%s\" key", p_u_5._input:get_key_display_str(v_u_4.KEY_CHAT_WINDOW_FOCUS))
                    end;
                    v_u_12.Visible = true
                else
                    v_u_12.Visible = false
                end;
                v_u_9.ZIndex = 2
            end;
        end;
        v_u_8.is_scrolled_to_bottom = function(_) --[[ Name: is_scrolled_to_bottom ]] --[[ Line: 187 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            local l_Offset_1 = v_u_9.CanvasSize.Y.Offset
            local l_Y_0 = v_u_9.AbsoluteWindowSize.Y
            return l_Offset_1 < l_Y_0 and true or l_Offset_1 - v_u_9.CanvasPosition.Y <= l_Y_0 + 5;
        end;
        local v_u_27 = Vector2.new()
        v_u_8.fit_to_text = function(p28) --[[ Name: fit_to_text ]] --[[ Line: 195 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_1, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_9, (ref 6): v_u_13, (ref 7): v_u_27, (ref 8): l_Offset_0, (copy 9): p_u_7, (copy 10): p_u_6 ]]
            if v_u_14 == false then
                v_u_14 = true
                local v29 = v_u_1:get_text_size(v_u_11.Text, v_u_11.TextSize, v_u_11.Font, Vector2.new(v_u_11.AbsoluteSize.X, 10000))
                v_u_11.Size = UDim2.new(v_u_11.Size.X.Scale, v_u_11.Size.X.Offset, v_u_11.Size.Y.Scale, v29.Y)
                v_u_12.Size = v_u_11.Size
                local l_Y_1 = v29.Y
                if v_u_11.TextSize * 4 < l_Y_1 then
                    l_Y_1 = v_u_11.TextSize * 4
                    local v30 = p28:is_scrolled_to_bottom()
                    v_u_9.CanvasSize = UDim2.new(0, 0, 0, v29.Y + 11)
                    if v30 then
                        v_u_9.CanvasPosition = Vector2.new(0, v_u_9.CanvasSize.Y.Offset)
                    end;
                else
                    v_u_9.CanvasSize = UDim2.new(0, 0, 0, 0)
                    v_u_9.CanvasPosition = Vector2.new(0, 0)
                end;
                local v31 = v_u_13
                v_u_13 = l_Y_1 + 22
                local l_AbsolutePosition_0 = v_u_11.AbsolutePosition
                if l_AbsolutePosition_0 ~= v_u_27 then
                    l_Offset_0 = v_u_13
                    p_u_7.Size = UDim2.new(p_u_7.Size.X.Scale, p_u_7.Size.X.Offset, p_u_7.Size.Y.Scale, l_Offset_0)
                end;
                v_u_27 = l_AbsolutePosition_0
                if v_u_13 ~= v31 then
                    p_u_6:on_layout_changed()
                end;
                v_u_14 = false
            end;
        end;
        v_u_8.update = function(_, p32) --[[ Name: update ]] --[[ Line: 238 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): l_Offset_0, (ref 3): v_u_13, (ref 4): v_u_2, (copy 5): p_u_7 ]]
            if v_u_3:flt_cmp_delta(l_Offset_0, v_u_13, 0.25) ~= true then
                l_Offset_0 = v_u_2:expt_sec(l_Offset_0, v_u_13, 0.25, p32)
                p_u_7.Size = UDim2.new(p_u_7.Size.X.Scale, p_u_7.Size.X.Offset, p_u_7.Size.Y.Scale, l_Offset_0)
            end;
        end;
        v_u_8.get_height = function(_) --[[ Name: get_height ]] --[[ Line: 245 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return v_u_13;
        end;
        v_u_8.capture_focus = function(_) --[[ Name: capture_focus ]] --[[ Line: 247 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11:CaptureFocus()
        end;
        v_u_8.set_alpha = function(_, p33) --[[ Name: set_alpha ]] --[[ Line: 251 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_3, (ref 3): v_u_2, (ref 4): v_u_11, (ref 5): v_u_12 ]]
            v_u_10.BackgroundTransparency = v_u_3:tra(v_u_2:Lerp(0, 0.4, p33))
            v_u_11.TextTransparency = v_u_3:tra(v_u_2:Lerp(0, 0.6, p33))
            v_u_12.TextTransparency = v_u_3:tra(v_u_2:Lerp(0, 0.6, p33))
        end;
        f_cons()
        return v_u_8;
    end
};
