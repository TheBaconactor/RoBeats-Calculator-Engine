-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.TextSizeCache)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
require(game.ReplicatedStorage.Shared.InputUtil)
local v6 = {}
local v_u_7 = {
    ["None"] = 0,
    ["ActionTriggered"] = 1
}
local v_u_8 = v_u_3:new():add_set_from_table_list({ v_u_5.ExtraDataType.JoinCustomChannel, v_u_5.ExtraDataType.GuildInvite })
v6.new = function(_, p_u_9, p_u_10, p_u_11, p_u_12) --[[ Name: new ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_2, (copy 5): v_u_3, (copy 6): v_u_5, (copy 7): v_u_8 ]]
    local v_u_13 = {}
    local v_u_14 = true
    local v_u_15 = nil
    local v_u_16 = nil
    local v_u_17 = ""
    local v_u_18 = nil
    local l_None_0 = v_u_7.None
    v_u_13.get_message_data = function(_) --[[ Name: get_message_data ]] --[[ Line: 37 ]]
        --[[ Upvalues: (copy 1): p_u_12 ]]
        return p_u_12;
    end;
    v_u_13.set_message_channel = function(p19, p20) --[[ Name: set_message_channel ]] --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_14 ]]
        if v_u_15 ~= p20 then
            v_u_15 = p20
            v_u_14 = true
        end;
        return p19;
    end;
    v_u_13.set_message_name = function(p21, p22) --[[ Name: set_message_name ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_14 ]]
        if v_u_16 ~= p22 then
            v_u_16 = p22
            v_u_14 = true
        end;
        return p21;
    end;
    v_u_13.set_message_text = function(p23, p24) --[[ Name: set_message_text ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_14 ]]
        if v_u_17 ~= p24 then
            v_u_17 = p24
            v_u_14 = true
        end;
        return p23;
    end;
    v_u_13.set_message_extra_data = function(p25, p26) --[[ Name: set_message_extra_data ]] --[[ Line: 63 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_14 ]]
        v_u_18 = p26:get_icon()
        v_u_14 = true
        return p25;
    end;
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local l_SourceSansBold_0 = Enum.Font.SourceSansBold
    local v_u_32 = Color3.new(1, 1, 1)
    local v_u_33 = -1
    v_u_13.set_id = function(p34, p35) --[[ Name: set_id ]] --[[ Line: 80 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        v_u_33 = p35
        return p34;
    end;
    v_u_13.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 81 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33;
    end;
    local function _(p36) --[[ Name: format_text_display ]] --[[ Line: 83 ]]
        --[[ Upvalues: (copy 1): l_SourceSansBold_0, (copy 2): v_u_32 ]]
        local l_Left_0 = Enum.TextXAlignment.Left
        local l_Top_0 = Enum.TextYAlignment.Top
        p36.BackgroundTransparency = 1
        p36.Selectable = false
        p36.Font = l_SourceSansBold_0
        p36.TextSize = 18
        p36.TextXAlignment = l_Left_0
        p36.TextYAlignment = l_Top_0
        p36.TextTransparency = 0
        p36.TextStrokeTransparency = 0.75
        p36.TextColor3 = v_u_32
        p36.Visible = true
    end;
    local function _(p37) --[[ Name: get_udim2_size_for_text ]] --[[ Line: 102 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): l_SourceSansBold_0 ]]
        local v38 = v_u_1:get_text_size(p37, 18, l_SourceSansBold_0, Vector2.new(10000, 10000))
        return UDim2.new(0, v38.X, 0, v38.Y);
    end;
    v_u_13.get_formatted_channel = function(_) --[[ Name: get_formatted_channel ]] --[[ Line: 107 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        return (v_u_15 == nil or #v_u_15 == 0) and "" or string.format("(%s)", v_u_15);
    end;
    v_u_13.get_formatted_name = function(p39) --[[ Name: get_formatted_name ]] --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_18 ]]
        local v40 = (v_u_16 == nil or #v_u_16 <= 0) and "" or string.format("[%s]", v_u_16)
        local v41 = v_u_18 == nil and " " or string.rep(" ", 6)
        local v42 = p39:get_formatted_channel()
        if #v42 > 0 then
            return v42 .. v41 .. v40;
        else
            return v41 .. v40;
        end;
    end;
    v_u_13.get_formatted_text = function(p43) --[[ Name: get_formatted_text ]] --[[ Line: 131 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17 ]]
        if v_u_16 == nil or #v_u_16 == 0 then
            return p43:get_formatted_name() .. v_u_17;
        else
            return p43:get_formatted_name() .. " " .. v_u_17;
        end;
    end;
    v_u_13.cons = function(p44) --[[ Name: cons ]] --[[ Line: 140 ]]
        --[[ Upvalues: (ref 1): v_u_27, (copy 2): p_u_9, (ref 3): v_u_4, (copy 4): p_u_11, (ref 5): v_u_28, (copy 6): l_SourceSansBold_0, (copy 7): v_u_32, (ref 8): v_u_29, (ref 9): v_u_30, (ref 10): v_u_31 ]]
        v_u_27 = p_u_9._object_pool:depool_instance_type("Frame")
        v_u_27.Selectable = false
        v_u_27.Size = UDim2.new(1, 0, 0, 0)
        v_u_27.Visible = true
        v_u_27.BackgroundColor3 = v_u_4:color3(255, 255, 255)
        v_u_27.BackgroundTransparency = 1
        v_u_27.ZIndex = p_u_11
        v_u_28 = p_u_9._object_pool:depool_instance_type("TextLabel")
        local v45 = v_u_28
        local l_Left_1 = Enum.TextXAlignment.Left
        local l_Top_1 = Enum.TextYAlignment.Top
        v45.BackgroundTransparency = 1
        v45.Selectable = false
        v45.Font = l_SourceSansBold_0
        v45.TextSize = 18
        v45.TextXAlignment = l_Left_1
        v45.TextYAlignment = l_Top_1
        v45.TextTransparency = 0
        v45.TextStrokeTransparency = 0.75
        v45.TextColor3 = v_u_32
        v45.Visible = true
        v_u_28.Parent = v_u_27
        v_u_28.ZIndex = p_u_11 + 3
        v_u_28.AutoLocalize = false
        v_u_29 = p_u_9._object_pool:depool_instance_type("TextLabel")
        local v46 = v_u_29
        local l_Left_2 = Enum.TextXAlignment.Left
        local l_Top_2 = Enum.TextYAlignment.Top
        v46.BackgroundTransparency = 1
        v46.Selectable = false
        v46.Font = l_SourceSansBold_0
        v46.TextSize = 18
        v46.TextXAlignment = l_Left_2
        v46.TextYAlignment = l_Top_2
        v46.TextTransparency = 0
        v46.TextStrokeTransparency = 0.75
        v46.TextColor3 = v_u_32
        v46.Visible = true
        v_u_29.Parent = v_u_27
        v_u_29.ZIndex = p_u_11 + 2
        v_u_29.AutoLocalize = false
        v_u_30 = p_u_9._object_pool:depool_instance_type("ImageLabel")
        v_u_30.BackgroundTransparency = 1
        v_u_30.ImageTransparency = 0
        v_u_30.AutoLocalize = false
        v_u_30.Parent = v_u_27
        v_u_30.ZIndex = p_u_11 + 2
        v_u_30.Visible = false
        v_u_31 = p_u_9._object_pool:depool_instance_type("TextLabel")
        local v47 = v_u_31
        local l_Left_3 = Enum.TextXAlignment.Left
        local l_Top_3 = Enum.TextYAlignment.Top
        v47.BackgroundTransparency = 1
        v47.Selectable = false
        v47.Font = l_SourceSansBold_0
        v47.TextSize = 18
        v47.TextXAlignment = l_Left_3
        v47.TextYAlignment = l_Top_3
        v47.TextTransparency = 0
        v47.TextStrokeTransparency = 0.75
        v47.TextColor3 = v_u_32
        v47.Visible = true
        v_u_31.TextWrapped = true
        v_u_31.Parent = v_u_27
        v_u_31.ZIndex = p_u_11 + 1
        v_u_31.AutoLocalize = false
        p44:set_height(18)
    end;
    v_u_13.update_text = function(p48) --[[ Name: update_text ]] --[[ Line: 180 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_1, (copy 3): l_SourceSansBold_0, (ref 4): v_u_28, (ref 5): v_u_18, (ref 6): v_u_30, (ref 7): v_u_29, (ref 8): v_u_31 ]]
        local v49 = v_u_14
        if v_u_14 then
            v_u_14 = false
            local v50 = v_u_1:get_text_size(p48:get_formatted_channel(), 18, l_SourceSansBold_0, Vector2.new(10000, 10000))
            local v51 = UDim2.new(0, v50.X, 0, v50.Y)
            v_u_28.Size = v51
            v_u_28.Position = UDim2.new(0, 0, 0, 0)
            v_u_28.Text = p48:get_formatted_channel()
            if v_u_18 == nil then
                v_u_30.Visible = false
            else
                v_u_30.Visible = true
                v_u_30.Image = v_u_18
                v_u_30.Size = UDim2.new(0, v51.Y.Offset, 0, v51.Y.Offset)
                v_u_30.Position = UDim2.new(0, v51.X.Offset, 0, 2)
            end;
            local v52 = v_u_29
            local v53 = v_u_1:get_text_size(p48:get_formatted_name(), 18, l_SourceSansBold_0, Vector2.new(10000, 10000))
            v52.Size = UDim2.new(0, v53.X, 0, v53.Y)
            v_u_29.Position = UDim2.new(0, 0, 0, 0)
            v_u_29.Text = p48:get_formatted_name()
            v_u_31.Size = UDim2.new(1, 0, 1, 0)
            v_u_31.Position = UDim2.new(0, 0, 0, 0)
            v_u_31.Text = p48:get_formatted_text()
        end;
        return v49;
    end;
    v_u_13.destroy = function(_) --[[ Name: destroy ]] --[[ Line: 210 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_27, (ref 3): v_u_28, (ref 4): v_u_29, (ref 5): v_u_30, (ref 6): v_u_31 ]]
        p_u_9._object_pool:repool(v_u_27.ClassName, v_u_27)
        p_u_9._object_pool:repool(v_u_28.ClassName, v_u_28)
        p_u_9._object_pool:repool(v_u_29.ClassName, v_u_29)
        p_u_9._object_pool:repool(v_u_30.ClassName, v_u_30)
        p_u_9._object_pool:repool(v_u_31.ClassName, v_u_31)
    end;
    v_u_13.set_name_button_color = function(_, p54) --[[ Name: set_name_button_color ]] --[[ Line: 218 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        v_u_29.TextColor3 = p54
    end;
    v_u_13.set_channel_button_color = function(_, p55) --[[ Name: set_channel_button_color ]] --[[ Line: 219 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        v_u_28.TextColor3 = p55
    end;
    v_u_13.set_parent_uiobj = function(_, p56) --[[ Name: set_parent_uiobj ]] --[[ Line: 220 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        v_u_27.Parent = p56
    end;
    local v_u_57 = v_u_2:new(0, 0)
    local v_u_58 = -1
    v_u_13.set_position = function(_, p59) --[[ Name: set_position ]] --[[ Line: 224 ]]
        --[[ Upvalues: (copy 1): v_u_57, (ref 2): v_u_27 ]]
        v_u_57:set(p59.X, p59.Y)
        v_u_27.Position = UDim2.new(0, v_u_57._x, 0, v_u_57._y)
    end;
    v_u_13.get_position = function(_) --[[ Name: get_position ]] --[[ Line: 228 ]]
        --[[ Upvalues: (copy 1): v_u_57 ]]
        return Vector2.new(v_u_57._x, v_u_57._y);
    end;
    v_u_13.offset_position_by = function(_, p60) --[[ Name: offset_position_by ]] --[[ Line: 229 ]]
        --[[ Upvalues: (copy 1): v_u_57, (ref 2): v_u_27 ]]
        v_u_57:set(v_u_57._x + p60.X, v_u_57._y + p60.Y)
        v_u_27.Position = UDim2.new(0, v_u_57._x, 0, v_u_57._y)
    end;
    v_u_13.set_height = function(_, p61) --[[ Name: set_height ]] --[[ Line: 233 ]]
        --[[ Upvalues: (ref 1): v_u_58, (ref 2): v_u_27 ]]
        v_u_58 = p61
        v_u_27.Size = UDim2.new(1, 0, 0, v_u_58)
    end;
    v_u_13.get_height = function(_) --[[ Name: get_height ]] --[[ Line: 237 ]]
        --[[ Upvalues: (ref 1): v_u_58 ]]
        return v_u_58;
    end;
    v_u_13.get_height_for_text_width = function(p62, p63) --[[ Name: get_height_for_text_width ]] --[[ Line: 239 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): l_SourceSansBold_0 ]]
        return v_u_1:get_text_size(p62:get_formatted_text(), 18, l_SourceSansBold_0, Vector2.new(p63, 1000)).Y + 1;
    end;
    local v64 = v_u_3:new()
    local v65 = {}
    v65[v_u_5.ExtraDataType.JoinCustomChannel] = function(_) --[[ Line: 245 ]]
        --[[ Upvalues: (copy 1): p_u_9, (copy 2): p_u_12, (copy 3): v_u_13 ]]
        p_u_9._chat:request_join_custom_channel_of_id(p_u_12:get_extradata())
        v_u_13:set_message_text("Joining channel...")
    end
    v65[v_u_5.ExtraDataType.GuildInvite] = function(_) --[[ Line: 249 ]]
        --[[ Upvalues: (copy 1): v_u_13, (copy 2): p_u_9, (copy 3): p_u_12 ]]
        v_u_13:set_message_text("Joining team...")
        p_u_9._guild_manager:accept_invite_to_join_guild(p_u_12:get_extradata())
    end
    local v_u_66 = v64:add_table(v65)
    v_u_13.update = function(p67, p68) --[[ Name: update ]] --[[ Line: 255 ]]
        --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_12, (ref 3): l_None_0, (ref 4): v_u_7, (copy 5): p_u_10, (ref 6): v_u_31, (ref 7): v_u_27, (copy 8): p_u_9, (copy 9): v_u_66 ]]
        if v_u_8:contains(p_u_12:get_extradata_type()) then
            if l_None_0 == v_u_7.None and p_u_10:is_cursor_intersect_uiobject(v_u_31) then
                v_u_27.BackgroundTransparency = 0.85
                if p_u_9._chat:do_press_trigger() then
                    l_None_0 = v_u_7.ActionTriggered
                    if v_u_66:contains(p_u_12:get_extradata_type()) then
                        v_u_66:get(p_u_12:get_extradata_type())(p68)
                    end;
                    p67:update_text()
                    p_u_10:recalculate_all_message_positions()
                    return;
                end;
            else
                v_u_27.BackgroundTransparency = 1
            end;
        end;
    end;
    v_u_13:cons()
    return v_u_13;
end;
return v6;
