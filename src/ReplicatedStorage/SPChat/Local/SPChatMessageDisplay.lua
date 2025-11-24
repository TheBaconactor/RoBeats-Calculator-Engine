-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRect)
local v_u_4 = require(game.ReplicatedStorage.SPChat.Local.SPChatMessageDisplayElement)
local v_u_5 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
return {
    ["new"] = function(_, p_u_6, p_u_7) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_5, (copy 4): v_u_3, (copy 5): v_u_1 ]]
        local v8 = {}
        local v_u_9 = nil
        local v_u_10 = nil
        v8.get_base_frame = function(_) --[[ Name: get_base_frame ]] --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end;
        v8.get_scrolling_frame = function(_) --[[ Name: get_scrolling_frame ]] --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10;
        end;
        local v_u_11 = nil
        v8.set_base_frame_parent = function(_, p12) --[[ Name: set_base_frame_parent ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            v_u_9.Parent = p12
        end;
        v8.set_spuiobj_parent = function(_, p13) --[[ Name: set_spuiobj_parent ]] --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11 = p13
        end;
        local v_u_14 = v_u_2:new()
        v8.get_message_display_elements = function(_) --[[ Name: get_message_display_elements ]] --[[ Line: 28 ]]
            --[[ Upvalues: (copy 1): v_u_14 ]]
            return v_u_14;
        end;
        v8.cons = function(_) --[[ Name: cons ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_7, (ref 3): v_u_10 ]]
            v_u_9 = Instance.new("Frame")
            v_u_9.Selectable = false
            v_u_9.Size = UDim2.new(1, 0, 1, 0)
            v_u_9.BackgroundTransparency = 1
            v_u_9.ZIndex = p_u_7
            v_u_10 = Instance.new("ScrollingFrame")
            v_u_10.Selectable = false
            v_u_10.Name = "Scroller"
            v_u_10.BackgroundTransparency = 1
            v_u_10.BorderSizePixel = 0
            v_u_10.Position = UDim2.new(0, 0, 0, 3)
            v_u_10.Size = UDim2.new(1, -4, 1, -6)
            v_u_10.CanvasSize = UDim2.new(0, 0, 0, 0)
            v_u_10.ScrollBarThickness = 4
            v_u_10.ScrollingDirection = Enum.ScrollingDirection.Y
            v_u_10.Active = false
            v_u_10.Parent = v_u_9
            v_u_10.ZIndex = p_u_7
        end;
        v8.clear = function(_) --[[ Name: clear ]] --[[ Line: 52 ]]
            --[[ Upvalues: (copy 1): v_u_14 ]]
            for v15 = 1, v_u_14:count() do
                v_u_14:get(v15):destroy()
            end;
            v_u_14:clear()
        end;
        v8.destroy = function(p16) --[[ Name: destroy ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            v_u_9.Parent = nil
            p16:clear()
        end;
        v8.is_scrolled_to_bottom = function(_) --[[ Name: is_scrolled_to_bottom ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            local l_Offset_0 = v_u_10.CanvasSize.Y.Offset
            local l_Y_0 = v_u_10.AbsoluteWindowSize.Y
            return l_Offset_0 < l_Y_0 and true or l_Offset_0 - v_u_10.CanvasPosition.Y <= l_Y_0 + 5;
        end;
        v8.add_message = function(p17, p18) --[[ Name: add_message ]] --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_6, (copy 3): p_u_7, (copy 4): v_u_14, (ref 5): v_u_10, (ref 6): v_u_5 ]]
            local v19 = p17:is_scrolled_to_bottom()
            local v20 = v_u_4:new(p_u_6, p17, p_u_7 + 1, p18):set_message_name(p18:get_speaker_name()):set_message_channel(p18:get_channel_name()):set_message_text(p18:get_message()):set_message_extra_data(p18)
            v20:update_text()
            v_u_14:push_back(v20)
            v20:set_parent_uiobj(v_u_10)
            local l_AbsoluteSize_0 = v_u_10.AbsoluteSize
            local l_CanvasSize_0 = v_u_10.CanvasSize
            local v21 = v20:get_height_for_text_width(l_AbsoluteSize_0.X)
            v20:set_position(Vector2.new(0, l_CanvasSize_0.Y.Offset))
            v20:set_height(v21)
            local v22 = l_CanvasSize_0 + UDim2.new(0, 0, 0, v21)
            v_u_10.CanvasSize = v22
            if v19 then
                v_u_10.CanvasPosition = Vector2.new(0, (math.max(0, v22.Y.Offset - l_AbsoluteSize_0.Y)))
            end;
            if v_u_14:count() > v_u_5:get_channel_message_history_count() then
                Vector2.new(0, 0)
                local v23 = v_u_14:pop_front()
                local v24 = Vector2.new(0, -v23:get_height())
                v23:destroy()
                if v_u_14:count() > 0 then
                    v24 = Vector2.new(0, -v_u_14:get(1):get_position().Y)
                end;
                for v25 = 1, v_u_14:count() do
                    v_u_14:get(v25):offset_position_by(v24)
                end;
                v_u_10.CanvasSize = v_u_10.CanvasSize + UDim2.new(0, v24.X, 0, v24.Y)
            end;
            return v20;
        end;
        v8.recalculate_all_message_positions = function(_) --[[ Name: recalculate_all_message_positions ]] --[[ Line: 138 ]]
            --[[ Upvalues: (copy 1): v_u_14, (ref 2): v_u_10 ]]
            local v26 = 0
            for v27 = 1, v_u_14:count() do
                local v28 = v_u_14:get(v27)
                local v29 = v28:get_height_for_text_width(v_u_10.AbsoluteSize.X)
                v28:set_position(Vector2.new(0, v26))
                v28:set_height(v29)
                v26 = v26 + v28:get_height()
            end;
            v_u_10.CanvasSize = UDim2.new(v_u_10.CanvasSize.X.Scale, v_u_10.CanvasSize.X.Offset, v_u_10.CanvasSize.Y.Scale, v26)
        end;
        v8.relayout_starting_at_element_index = function(p30, p31) --[[ Name: relayout_starting_at_element_index ]] --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_14 ]]
            local v32 = p30:is_scrolled_to_bottom()
            local v33 = Vector2.new(0, 0)
            local l_X_0 = v_u_10.AbsoluteSize.X
            for v34 = p31, v_u_14:count() do
                local v35 = v_u_14:get(v34)
                if v33.Magnitude > 0 then
                    v35:set_position(v35:get_position() + v33)
                end;
                local v36 = v35:get_height()
                local v37 = v35:get_height_for_text_width(l_X_0)
                if v36 ~= v37 then
                    v35:set_height(v37)
                    v33 = v33 + Vector2.new(0, v37 - v36)
                end;
            end;
            v_u_10.CanvasSize = v_u_10.CanvasSize + UDim2.new(0, 0, 0, v33.Y)
            if v32 then
                v_u_10.CanvasPosition = v_u_10.CanvasPosition + v33
            end;
        end;
        local v_u_38 = v_u_3:new()
        local v_u_39 = v_u_3:new()
        v8.is_cursor_intersect_uiobject = function(_, p40) --[[ Name: is_cursor_intersect_uiobject ]] --[[ Line: 186 ]]
            --[[ Upvalues: (copy 1): p_u_6, (ref 2): v_u_1, (copy 3): v_u_39, (ref 4): v_u_9, (copy 5): v_u_38 ]]
            local v41 = p_u_6._spui:get_cursor_nxy()
            v_u_1:get_ui_object_nrect(p40, v_u_39)
            v_u_1:get_ui_object_nrect(v_u_9, v_u_38)
            local v42 = v_u_38:contains_vec2(v41)
            if v42 then
                v42 = v_u_39:contains_vec2(v41)
            end;
            return v42;
        end;
        v8.update = function(_, p43) --[[ Name: update ]] --[[ Line: 193 ]]
            --[[ Upvalues: (copy 1): v_u_14 ]]
            for v44 = 1, v_u_14:count() do
                v_u_14:get(v44):update(p43)
            end;
        end;
        v8:cons()
        return v8;
    end
};
