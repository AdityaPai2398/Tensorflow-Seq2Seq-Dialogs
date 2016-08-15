import tensorflow as tf
import numpy as np
import time
import re
from itertools import izip
import argparse


def train_model(path, seq_size, units, layers, trainiterations, batch_size, dloss, dout, dictionary, restore=False):

    x = tf.placeholder(tf.int32, shape=[None, None])
    y = tf.placeholder(tf.int32, shape=[None, None])
    targets = tf.placeholder(tf.int32, shape=[None, None])

    rvsdictionary = dict(izip(dictionary.values(), dictionary.keys()))
    dictsize = len(dictionary)

    filename_queue = tf.train.string_input_producer([str(path) + "dialogs.csv"])

    reader = tf.TextLineReader()
    key, value = reader.read(filename_queue)

    record_defaults = [[""], [""]]
    col1, col2 = tf.decode_csv(value, record_defaults=record_defaults)

    features = tf.pack(col1)
    labels = tf.pack(col2)

    features, labels = tf.train.batch([features, labels], batch_size, num_threads=4)

    teminp = []
    temoutput = []
    temtarget = []

    for o in range(seq_size):
        teminp.append(x[:, o])
        temoutput.append(y[:, o])
        temtarget.append(targets[:, o])

    W1 = tf.placeholder(tf.float32, shape=[batch_size, seq_size])
    W1_0 = []
    for j in range(seq_size):
        W1_0.append(W1[:, j])

    cell1 = tf.nn.rnn_cell.GRUCell(units)
    cell = tf.nn.rnn_cell.MultiRNNCell([cell1] * layers)

    rnn, state = tf.nn.seq2seq.embedding_attention_seq2seq(teminp, temoutput, cell, dictsize, dictsize, 100)

    logits = tf.nn.seq2seq.sequence_loss(rnn, temtarget, W1_0)

    train = tf.train.AdagradOptimizer(0.1).minimize(logits)

    saver = tf.train.Saver()

    init_op = tf.initialize_all_variables()
    sess = tf.InteractiveSession()
    sess.run(init_op)

    coord = tf.train.Coordinator()
    threads = tf.train.start_queue_runners(sess=sess, coord=coord)

    if restore:
        saver.restore(sess, str(path) + "model.ckpt")

    for i in range(trainiterations):
        cutime = time.time() * 1000
        data, outputs = sess.run([features, labels])

        databatch = []
        labelsbatch = []
        tbatch = []

        for line in data:
            data = re.split("\s", line)
            tempdata = []
            for word in data:
                if word != '':
                    tempdata.append(dictionary[word])
            for p in range(seq_size - len(tempdata)):
                tempdata.append(dictionary["NULL"])
            tempdata.reverse()
            databatch.append(tempdata)

        for line in outputs:
            outputs = re.split("\s", line)
            outputs.insert(0, "GO")
            tempoutputs = []
            for word in outputs:
                if word != '':
                    tempoutputs.append(dictionary[word])
            for p in range(seq_size - len(tempoutputs)):
                tempoutputs.append(dictionary["NULL"])
            t = [tempoutputs[k + 1] for k in range(len(tempoutputs) - 1)]
            t = np.append(np.array(t), dictionary["NULL"])
            labelsbatch.append(tempoutputs)
            tbatch.append(t)

        databatch = np.array(databatch)
        labelsbatch = np.array(labelsbatch)
        tbatch = np.array(tbatch)

        sess.run(train, feed_dict={x: databatch, y: labelsbatch, targets: tbatch, W1: np.ones([batch_size, seq_size], dtype=np.float32)})

        if dout:
            tempout = sess.run(rnn, feed_dict={x: databatch, y: labelsbatch})
            tempdata = np.split(np.array(tempout), batch_size, 1)

            data = []
            for sent in tempdata:
                temdata = []

                for word in sent:
                    temdata.append(rvsdictionary[np.argmax(word)])
                temdata = [item for item in temdata if item != 'NULL']
                data.append(temdata)
            print(data)

        if dloss:
            loss = sess.run(logits, feed_dict={x: databatch, y: labelsbatch, targets: tbatch, W1: np.ones([batch_size, seq_size], dtype=np.float32)})
            print("Time: " + str((time.time() * 1000) - cutime) + " Iteration: " + str(i) + " Loss: " + str(loss))
        else:
            print("Time: " + str((time.time() * 1000) - cutime) + " Iteration: " + str(i))

    saver.save(sess, str(path) + "model.ckpt")

    coord.request_stop()
    coord.join(threads)


def create_dictionary(path):

    csv = np.loadtxt(str(path) + "dialogs.csv", delimiter=",", dtype="string", skiprows=0)

    tempdict = []
    dictionary = set(["NULL", "GO"])

    maxlen = 0
    for row in csv:
        for line in row:
            lines = str(line).split()
            lines = " ".join(lines)
            lines = lines.replace(". ", " ")
            lines = lines.replace("!", "")
            lines = lines.replace("?", "")
            lines = lines.replace("-", " ")
            lines = lines.replace(",", " ")
            lines = lines.replace("/", "")
            lines = lines.replace("' ", " ")
            lines = lines.replace(" '", " ")
            lines = lines.replace(" ' ", " ")
            lines = lines.replace("\"", "")
            lines = lines.replace("*", "")
            lines = lines.replace(";", "")
            lines = lines.replace(":", "")
            lines = lines.replace("<u>", "")
            lines = lines.replace("<b>", "")
            lines = lines.replace("_", "")
            lines = lines.replace("]", "")
            lines = lines.replace("[", "")
            lines = lines.replace("}", "")
            lines = lines.replace("{", "")
            lines = lines.replace(")", "")
            lines = lines.replace("(", "")
            lines = lines.replace("@", "")
            lines = lines.replace("#", "")
            lines = lines.replace("$", "")
            lines = lines.replace("%", "")
            lines = lines.replace("^", "")
            lines = lines.replace("&", "")
            lines = lines.replace("+", "")
            lines = lines.replace("=", "")
            lines = lines.replace("|", "")
            lines = lines.replace("\\", "")
            lines = lines.replace("<", "")
            lines = lines.replace(">", "")
            lines = [item for item in lines if not item.isdigit()]
            line = ''.join(lines).strip()

            words = re.split(" ", line)
            tempdict.extend(words)

            if len(words) > maxlen:
                maxlen = len(words)
    dictionary = dictionary.union(tempdict)

    dictsize = len(dictionary)

    count = []

    for i in range(dictsize):
        count.append(i)

    dictionary = dict(izip(list(dictionary), count))
    # print("Number of words in dictionary: " + str(len(dictionary)))
    # print("Max Length: " + str(maxlen))
    # print("Number of lines: " + str(csv.shape[0]))

    return int(maxlen), dictionary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dialog_path", type=str, help="path to the dialog csv ex: \"/user/dialog_folder/\"")
    parser.add_argument("units", type=int, help="number of units in a GRU layer")
    parser.add_argument("layers", type=int, help="number of GRU layers")
    parser.add_argument("train_iterations", type=int, help="number of training iterations")
    parser.add_argument("batch_size", type=int, help="number of units in a batch")
    parser.add_argument("--restore", help="if you want to restore from a old model", action="store_true")
    parser.add_argument("--display_out", help="if you want to see the outputs from training", action="store_true")
    parser.add_argument("--display_loss", help="if you want to see the loss from training", action="store_true")
    args = parser.parse_args()

    length, dictionary = create_dictionary(args.dialog_path)

    if args.restore:
        train_model(args.dialog_path, length + 1, args.units, args.layers, args.train_iterations, args.batch_size, args.display_loss, args.display_out, dictionary, restore=args.restore)
    else:
        train_model(args.dialog_path, length + 1, args.units, args.layers, args.train_iterations, args.batch_size, args.display_loss, args.display_out, dictionary)